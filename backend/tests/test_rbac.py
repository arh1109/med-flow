import pytest


# ---------------------------------------------------------------------------
# Authentication boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,url",
    [
        ("GET", "/hospitals"),
        ("GET", "/equipments"),
        ("GET", "/work_orders"),
        ("GET", "/users"),
        ("GET", "/diagnostic_logs"),
    ],
)
async def test_protected_routes_reject_anonymous_users(
    client,
    method,
    url,
):
    response = await client.request(
        method,
        url,
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Hospitals
#
# Intended policy:
#   Clinical Admin   -> read + write
#   Auditor          -> read only
#   Field Technician -> read only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "admin",
        "auditor",
        "technician",
    ],
)
async def test_all_roles_can_read_hospitals(
    client,
    rbac_headers,
    role,
):
    response = await client.get(
        "/hospitals",
        headers=rbac_headers[role],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_admin_can_create_hospital(
    client,
    rbac_headers,
):
    response = await client.post(
        "/hospitals",
        headers=rbac_headers["admin"],
        json={
            "name": "RBAC Test Hospital",
            "location_region": "TEST-EAST",
            "capacity": 50,
            "supervisor_id": 9901,
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_create_hospital(
    client,
    rbac_headers,
    role,
):
    response = await client.post(
        "/hospitals",
        headers=rbac_headers[role],
        json={
            "name": "Forbidden Hospital",
            "location_region": "TEST-WEST",
            "capacity": 25,
            "supervisor_id": 9902,
        },
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Users
#
# Intended CURRENT policy from the menu/RBAC design:
#   Clinical Admin   -> read + write
#   Auditor          -> read only
#   Field Technician -> no access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_can_read_users(
    client,
    rbac_headers,
):
    response = await client.get(
        "/users",
        headers=rbac_headers["admin"],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auditor_can_read_users(
    client,
    rbac_headers,
):
    response = await client.get(
        "/users",
        headers=rbac_headers["auditor"],
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_technician_cannot_read_users(
    client,
    rbac_headers,
):
    response = await client.get(
        "/users",
        headers=rbac_headers["technician"],
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_user(
    client,
    rbac_headers,
):
    response = await client.post(
        "/users",
        headers=rbac_headers["admin"],
        json={
            "username": "created_by_rbac_test",
            "password": "AnotherPassword123!",
            "role": "Auditor",
            "technician_id": None,
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_create_user(
    client,
    rbac_headers,
    role,
):
    response = await client.post(
        "/users",
        headers=rbac_headers[role],
        json={
            "username": f"forbidden_{role}",
            "password": "AnotherPassword123!",
            "role": "Auditor",
            "technician_id": None,
        },
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Work Orders
#
# Intended policy:
#   Clinical Admin   -> full CRUD
#   Auditor          -> read only
#   Field Technician -> read assigned work orders; status-only update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "admin",
        "auditor",
        "technician",
    ],
)
async def test_all_roles_can_access_work_order_list(
    client,
    rbac_headers,
    role,
):
    response = await client.get(
        "/work_orders",
        headers=rbac_headers[role],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_create_work_order(
    client,
    rbac_headers,
    role,
):
    # FK ids do not need to exist here: the role dependency should reject
    # the request before the route attempts the insert.
    response = await client.post(
        "/work_orders",
        headers=rbac_headers[role],
        json={
            "title": "Forbidden Work Order",
            "priority": "Medium",
            "status": "Pending",
            "equipment_id": 999001,
            "technician_id": 999002,
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_fully_edit_work_order(
    client,
    rbac_headers,
    role,
):
    response = await client.put(
        "/work_orders/999999",
        headers=rbac_headers[role],
        json={
            "title": "Forbidden Edit",
            "priority": "Medium",
            "status": "Pending",
            "equipment_id": 999001,
            "technician_id": 999002,
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_delete_work_order(
    client,
    rbac_headers,
    role,
):
    response = await client.delete(
        "/work_orders/999999",
        headers=rbac_headers[role],
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Equipment
#
# Intended policy:
#   Clinical Admin   -> full CRUD
#   Auditor          -> read only
#   Field Technician -> assigned equipment read only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "admin",
        "auditor",
        "technician",
    ],
)
async def test_all_roles_can_access_equipment_list(
    client,
    rbac_headers,
    role,
):
    response = await client.get(
        "/equipments",
        headers=rbac_headers[role],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "auditor",
        "technician",
    ],
)
async def test_non_admin_cannot_create_equipment(
    client,
    rbac_headers,
    role,
):
    response = await client.post(
        "/equipments",
        headers=rbac_headers[role],
        json={
            "serial_number": f"RBAC-{role}",
            "model": "Test Infusion Pump",
            "status": "Operational",
            "battery_level": 75,
            "hospital_id": None,
        },
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Analytics
#
# Current intended UI/RBAC policy:
#   Clinical Admin -> allowed
#   Auditor        -> allowed
#   Technician     -> denied
#
# These tests intentionally enforce backend security too; hiding the Analytics
# menu in React should not be the only restriction.
# ---------------------------------------------------------------------------


ANALYTICS_ENDPOINTS = [
    "/work_orders/reliability",
    "/work_orders/discrepancies",
    "/hospitals/maintenance-flags",
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ANALYTICS_ENDPOINTS,
)
@pytest.mark.parametrize(
    "role",
    [
        "admin",
        "auditor",
    ],
)
async def test_admin_and_auditor_can_view_analytics(
    client,
    rbac_headers,
    role,
    url,
):
    response = await client.get(
        url,
        headers=rbac_headers[role],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url",
    ANALYTICS_ENDPOINTS,
)
async def test_technician_cannot_view_analytics(
    client,
    rbac_headers,
    url,
):
    response = await client.get(
        url,
        headers=rbac_headers["technician"],
    )

    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Diagnostic reports
#
# All authenticated roles can list diagnostic logs.
# Only Admin + Field Technician may upload.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role",
    [
        "admin",
        "auditor",
        "technician",
    ],
)
async def test_all_roles_can_list_diagnostic_logs(
    client,
    rbac_headers,
    role,
):
    response = await client.get(
        "/diagnostic_logs",
        headers=rbac_headers[role],
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auditor_cannot_upload_diagnostic_report(
    client,
    rbac_headers,
):
    response = await client.post(
        "/diagnostic_logs",
        headers=rbac_headers["auditor"],
        data={
            "work_order_id": "999999",
        },
        files={
            "file": (
                "report.txt",
                b"pytest report",
                "text/plain",
            ),
        },
    )

    # RBAC should run before work-order/file persistence logic.
    assert response.status_code == 403
