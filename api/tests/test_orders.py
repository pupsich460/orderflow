from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from shared.database import get_session


@pytest.mark.asyncio
async def test_create_order_missing_item():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/orders/", json={"qty": 2})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_order_invalid_qty_type():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/orders/", json={"item": "Наушники", "qty": "два"})
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_order_success():
    mock_session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 1
        obj.status = "pending"
        obj.created_at = datetime.now(timezone.utc)

    mock_session.refresh = fake_refresh

    async def override_get_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_get_session

    with patch("routers.v1.orders.publish_order", new_callable=AsyncMock):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/v1/orders/", json={"item": "Наушники", "qty": 2})

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["item"] == "Наушники"
    assert response.json()["qty"] == 2