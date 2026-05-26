"""Tests for the team-kickoff promotion.

Carries over the relevant Flatpack TEST_CASES:
- 'computeProgress counts done items' → test_progress_summary_counts_done
- 'toMarkdown includes section titles' → test_markdown_includes_section_titles
- 'toMarkdown checks items that are marked done' → test_markdown_checks_done_items

Plus a new test the Flatpack couldn't have written:
- test_cross_run_isolation — ticking in run A doesn't affect run B.
"""

import pytest

from tests.conftest import TEST_ADMIN_EMAIL


SAMPLE_TEMPLATE = {
    "name": "Kickoff",
    "sections": [
        {
            "title": "Scope",
            "position": 0,
            "items": [
                {"text": "Goal stated in one sentence", "why": None, "position": 0},
                {"text": "Non-goals listed", "why": None, "position": 1},
            ],
        },
        {
            "title": "People",
            "position": 1,
            "items": [
                {"text": "Owner identified", "why": None, "position": 0},
                {"text": "Reviewers identified", "why": None, "position": 1},
            ],
        },
    ],
}


async def _login(client) -> dict[str, str]:
    resp = await client.post(
        "/api/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "testpass"},
    )
    assert resp.status_code == 200
    return {"X-CSRF-Token": resp.cookies["csrf_token"]}


async def _create_template(client, headers) -> dict:
    resp = await client.post(
        "/api/admin/checklist-templates",
        json=SAMPLE_TEMPLATE,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _start_run(client, headers, template_id: str, project_handle: str) -> dict:
    resp = await client.post(
        "/api/admin/runs",
        json={"template_id": template_id, "project_handle": project_handle},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _list_progress(client, run_id: str) -> list[dict]:
    resp = await client.get(f"/api/admin/runs/{run_id}/progress")
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_template_creation_starts_at_version_1(client):
    headers = await _login(client)
    template = await _create_template(client, headers)
    assert template["version"] == 1
    assert template["is_active"] is True


@pytest.mark.asyncio
async def test_new_template_with_same_name_increments_version(client):
    headers = await _login(client)
    t1 = await _create_template(client, headers)
    t2 = await _create_template(client, headers)
    assert t2["version"] == 2
    assert t2["is_active"] is True

    # The prior should now be deactivated.
    detail = await client.get(f"/api/admin/checklist-templates/{t1['id']}")
    assert detail.status_code == 200
    assert detail.json()["is_active"] is False


@pytest.mark.asyncio
async def test_run_start_snapshots_template_version_and_creates_progress(client):
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "Acme Q2 kickoff")
    assert run["template_version"] == template["version"]

    progress = await _list_progress(client, run["id"])
    # 2 sections × 2 items = 4 progress rows.
    assert len(progress) == 4
    assert all(p["done"] is False for p in progress)


@pytest.mark.asyncio
async def test_progress_summary_counts_done(client):
    """Carry-over of the Flatpack's 'computeProgress counts done items' test."""
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "X")
    progress = await _list_progress(client, run["id"])

    # Tick the first item.
    tick = await client.patch(
        f"/api/admin/runs/{run['id']}/progress/{progress[0]['item_id']}",
        json={"done": True},
        headers=headers,
    )
    assert tick.status_code == 200, tick.text
    assert tick.json()["done"] is True

    summary = await client.get(f"/api/admin/runs/{run['id']}/summary")
    assert summary.status_code == 200
    body = summary.json()
    assert body["done"] == 1
    assert body["total"] == 4
    assert body["pct"] == 25


@pytest.mark.asyncio
async def test_markdown_includes_section_titles(client):
    """Carry-over of 'toMarkdown includes section titles'."""
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "X")

    md = await client.get(f"/api/admin/runs/{run['id']}/markdown")
    assert md.status_code == 200
    text = md.text
    assert "## Scope" in text
    assert "## People" in text


@pytest.mark.asyncio
async def test_markdown_checks_done_items(client):
    """Carry-over of 'toMarkdown checks items that are marked done'."""
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "X")
    progress = await _list_progress(client, run["id"])
    # Tick the second item.
    await client.patch(
        f"/api/admin/runs/{run['id']}/progress/{progress[1]['item_id']}",
        json={"done": True},
        headers=headers,
    )
    md = await client.get(f"/api/admin/runs/{run['id']}/markdown")
    assert md.status_code == 200
    # Exactly one ticked line (the others remain '- [ ]').
    assert md.text.count("- [x]") == 1
    assert md.text.count("- [ ]") == 3


@pytest.mark.asyncio
async def test_untick_clears_attribution(client):
    """Decision item 3: un-ticking clears done_by/done_at."""
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "X")
    progress = await _list_progress(client, run["id"])

    # Tick.
    tick = await client.patch(
        f"/api/admin/runs/{run['id']}/progress/{progress[0]['item_id']}",
        json={"done": True},
        headers=headers,
    )
    assert tick.json()["done_by_id"] is not None
    assert tick.json()["done_at"] is not None

    # Untick.
    untick = await client.patch(
        f"/api/admin/runs/{run['id']}/progress/{progress[0]['item_id']}",
        json={"done": False},
        headers=headers,
    )
    assert untick.status_code == 200
    body = untick.json()
    assert body["done"] is False
    assert body["done_by_id"] is None
    assert body["done_at"] is None


@pytest.mark.asyncio
async def test_cross_run_isolation(client):
    """A new test the Flatpack couldn't have: ticking in run A doesn't
    affect run B."""
    headers = await _login(client)
    template = await _create_template(client, headers)
    run_a = await _start_run(client, headers, template["id"], "Engagement A")
    run_b = await _start_run(client, headers, template["id"], "Engagement B")

    # Tick the first item in run A.
    progress_a = await _list_progress(client, run_a["id"])
    await client.patch(
        f"/api/admin/runs/{run_a['id']}/progress/{progress_a[0]['item_id']}",
        json={"done": True},
        headers=headers,
    )

    # Run B's progress is untouched.
    progress_b = await _list_progress(client, run_b["id"])
    assert all(p["done"] is False for p in progress_b)


@pytest.mark.asyncio
async def test_run_completion_sets_completed_at(client):
    headers = await _login(client)
    template = await _create_template(client, headers)
    run = await _start_run(client, headers, template["id"], "X")
    assert run["completed_at"] is None

    patch = await client.patch(
        f"/api/admin/runs/{run['id']}/status",
        json={"status": "completed"},
        headers=headers,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None


@pytest.mark.asyncio
async def test_anonymous_template_create_is_forbidden(client):
    resp = await client.post(
        "/api/admin/checklist-templates",
        json=SAMPLE_TEMPLATE,
    )
    assert resp.status_code in (401, 403)
