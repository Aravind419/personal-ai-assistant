import pytest
from httpx import AsyncClient
from app.memory.embeddings import LocalSemanticEmbeddingProvider, cosine_similarity


@pytest.mark.asyncio
async def test_local_semantic_embedding_generation():
    provider = LocalSemanticEmbeddingProvider(dimension=384)
    assert provider.dimension == 384
    assert provider.provider_name == "local"

    # Similar text should have higher cosine similarity than unrelated text
    v1 = await provider.embed_text("The user loves Python and FastAPI backend development")
    v2 = await provider.embed_text("User prefers developing backends with Python and FastAPI")
    v3 = await provider.embed_text("Astronomy and planetary exploration of Saturn rings")

    sim_12 = cosine_similarity(v1, v2)
    sim_13 = cosine_similarity(v1, v3)

    assert len(v1) == 384
    assert len(v2) == 384
    assert len(v3) == 384
    assert sim_12 > 0.45
    assert sim_12 > sim_13


@pytest.mark.asyncio
async def test_memory_crud_and_search_flow(async_client: AsyncClient):
    # 1. Create a memory
    create_res = await async_client.post(
        "/api/v1/memories",
        json={
            "content": "User prefers concise Python 3.13 code with strict type hints.",
            "category": "preferences",
            "importance": 0.85,
            "confidence": 0.95,
            "metadata": {"topic": "python_standards"},
        },
    )
    assert create_res.status_code == 201
    mem = create_res.json()
    mem_id = mem["id"]
    assert mem["content"] == "User prefers concise Python 3.13 code with strict type hints."
    assert mem["category"] == "preferences"
    assert mem["importance"] == 0.85
    assert mem["confidence"] == 0.95
    assert mem["embedding_dim"] == 384
    assert mem["is_archived"] is False
    assert mem["metadata"] == {"topic": "python_standards"}

    # 2. Get memory by ID
    get_res = await async_client.get(f"/api/v1/memories/{mem_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == mem_id

    # 3. List memories with category filter
    list_res = await async_client.get("/api/v1/memories?category=preferences")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(m["id"] == mem_id for m in list_data["items"])

    # 4. Semantic Search
    search_res = await async_client.post(
        "/api/v1/memories/search",
        json={
            "query": "What are the user's coding preferences for Python?",
            "category": "preferences",
            "limit": 5,
            "threshold": 0.3,
        },
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert len(search_data) >= 1
    assert any(item["memory"]["id"] == mem_id for item in search_data)

    # 5. Update memory content (triggers re-embedding)
    patch_res = await async_client.patch(
        f"/api/v1/memories/{mem_id}",
        json={
            "content": "User exclusively writes Python 3.13 code with strict types and async patterns.",
            "importance": 0.90,
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["content"] == "User exclusively writes Python 3.13 code with strict types and async patterns."
    assert updated["importance"] == 0.90

    # 6. Archive memory
    archive_res = await async_client.post(f"/api/v1/memories/{mem_id}/archive?is_archived=true")
    assert archive_res.status_code == 200
    assert archive_res.json()["is_archived"] is True

    # 7. Verify not in default active list
    active_list = await async_client.get("/api/v1/memories")
    assert active_list.status_code == 200
    assert not any(m["id"] == mem_id for m in active_list.json()["items"])

    # 8. Unarchive and Delete
    unarchive_res = await async_client.post(f"/api/v1/memories/{mem_id}/archive?is_archived=false")
    assert unarchive_res.status_code == 200
    assert unarchive_res.json()["is_archived"] is False

    del_res = await async_client.delete(f"/api/v1/memories/{mem_id}")
    assert del_res.status_code == 204

    # 9. Verify 404 after deletion
    verify_res = await async_client.get(f"/api/v1/memories/{mem_id}")
    assert verify_res.status_code == 404


@pytest.mark.asyncio
async def test_memory_stats_endpoint(async_client: AsyncClient):
    res = await async_client.get("/api/v1/memories/stats")
    assert res.status_code == 200
    stats = res.json()
    assert "total_active" in stats
    assert "total_archived" in stats
    assert "category_distribution" in stats
    assert "recent_memories" in stats
    assert isinstance(stats["category_distribution"], dict)
