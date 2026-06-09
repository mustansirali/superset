# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import pytest
from marshmallow import ValidationError

from superset.row_level_security.schemas import (
    get_delete_ids_schema,
    RLSPostSchema,
    RLSPutSchema,
    RolesSchema,
    TablesSchema,
)


def test_get_delete_ids_schema_structure() -> None:
    assert get_delete_ids_schema == {"type": "array", "items": {"type": "integer"}}


def test_roles_schema_serializes() -> None:
    schema = RolesSchema()
    result = schema.dump({"name": "Admin", "id": 1})
    assert result == {"name": "Admin", "id": 1}


def test_tables_schema_serializes() -> None:
    schema = TablesSchema()
    result = schema.dump({"schema": "public", "table_name": "users", "id": 5})
    assert result == {"schema": "public", "table_name": "users", "id": 5}


def test_rls_post_schema_accepts_valid_data() -> None:
    schema = RLSPostSchema()
    data = {
        "name": "test_rule",
        "filter_type": "Regular",
        "tables": [1],
        "roles": [1],
        "clause": "id = 1",
    }
    result = schema.load(data)
    assert result["name"] == "test_rule"
    assert result["filter_type"] == "Regular"
    assert result["tables"] == [1]
    assert result["roles"] == [1]
    assert result["clause"] == "id = 1"


def test_rls_post_schema_rejects_missing_required_fields() -> None:
    schema = RLSPostSchema()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({})
    errors = exc_info.value.messages
    assert "name" in errors
    assert "filter_type" in errors
    assert "tables" in errors
    assert "roles" in errors
    assert "clause" in errors


def test_rls_post_schema_rejects_invalid_filter_type() -> None:
    schema = RLSPostSchema()
    data = {
        "name": "test_rule",
        "filter_type": "InvalidType",
        "tables": [1],
        "roles": [1],
        "clause": "id = 1",
    }
    with pytest.raises(ValidationError) as exc_info:
        schema.load(data)
    assert "filter_type" in exc_info.value.messages


def test_rls_post_schema_rejects_empty_name() -> None:
    schema = RLSPostSchema()
    data = {
        "name": "",
        "filter_type": "Regular",
        "tables": [1],
        "roles": [1],
        "clause": "id = 1",
    }
    with pytest.raises(ValidationError) as exc_info:
        schema.load(data)
    assert "name" in exc_info.value.messages


def test_rls_post_schema_rejects_empty_tables() -> None:
    schema = RLSPostSchema()
    data = {
        "name": "rule",
        "filter_type": "Regular",
        "tables": [],
        "roles": [1],
        "clause": "id = 1",
    }
    with pytest.raises(ValidationError) as exc_info:
        schema.load(data)
    assert "tables" in exc_info.value.messages


def test_rls_post_schema_accepts_optional_fields() -> None:
    schema = RLSPostSchema()
    data = {
        "name": "test_rule",
        "filter_type": "Base",
        "tables": [1],
        "roles": [1],
        "clause": "id = 1",
        "description": "A description",
        "group_key": "department",
    }
    result = schema.load(data)
    assert result["description"] == "A description"
    assert result["group_key"] == "department"


def test_rls_put_schema_accepts_partial_update() -> None:
    schema = RLSPutSchema()
    result = schema.load({"name": "new_name"})
    assert result == {"name": "new_name"}


def test_rls_put_schema_accepts_empty_payload() -> None:
    schema = RLSPutSchema()
    result = schema.load({})
    assert result == {}


def test_rls_put_schema_validates_filter_type_when_provided() -> None:
    schema = RLSPutSchema()
    with pytest.raises(ValidationError) as exc_info:
        schema.load({"filter_type": "Invalid"})
    assert "filter_type" in exc_info.value.messages
