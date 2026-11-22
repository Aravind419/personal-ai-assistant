import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_conversation_crud_flow(async_client: AsyncClient):
    # 1. Create conversation
    create_res = await async_client.post(
        "/api/v1/conversations",
        json={
            "title": "Test AI Discussion",
            "model": "openai/gpt-4o-mini",
            "system_prompt": "You are a concise assistant.",
        },
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    conv_id = conv["id"]
    assert conv["title"] == "Test AI Discussion"
    assert conv["model"] == "openai/gpt-4o-mini"
    assert conv["system_prompt"] == "You are a concise assistant."

    # 2. List conversations
    list_res = await async_client.get("/api/v1/conversations")
    assert list_res.status_code == 200
    conversations = list_res.json()
    assert any(c["id"] == conv_id for c in conversations)

    # 3. Retrieve conversation
    get_res = await async_client.get(f"/api/v1/conversations/{conv_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == conv_id
    assert isinstance(retrieved["messages"], list)

    # 4. Rename conversation
    patch_res = await async_client.patch(
        f"/api/v1/conversations/{conv_id}",
        json={"title": "Updated Discussion Title"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Updated Discussion Title"

    # 5. Delete conversation
    del_res = await async_client.delete(f"/api/v1/conversations/{conv_id}")
    assert del_res.status_code == 204

    # 6. Verify deleted
    verify_res = await async_client.get(f"/api/v1/conversations/{conv_id}")
    assert verify_res.status_code == 404
