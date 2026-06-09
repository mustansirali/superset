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
from unittest.mock import MagicMock, patch

import pytest

from superset.commands.exceptions import DatasourceNotFoundValidationError
from superset.commands.security.create import CreateRLSRuleCommand


def test_create_rls_command_validate_raises_on_missing_tables() -> None:
    data = {
        "name": "test_rule",
        "tables": [1, 2],
        "roles": [],
        "clause": "id = 1",
    }
    command = CreateRLSRuleCommand(data)
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [MagicMock()]

    with (
        patch(
            "superset.commands.security.create.populate_roles",
            return_value=[],
        ),
        patch("superset.commands.security.create.db") as mock_db,
    ):
        mock_db.session.query.return_value = mock_query
        with pytest.raises(DatasourceNotFoundValidationError):
            command.validate()


def test_create_rls_command_validate_populates_roles_and_tables() -> None:
    mock_role = MagicMock()
    mock_table_1 = MagicMock()
    mock_table_2 = MagicMock()

    data = {
        "name": "test_rule",
        "tables": [1, 2],
        "roles": [10],
        "clause": "id = 1",
    }
    command = CreateRLSRuleCommand(data)
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_table_1, mock_table_2]

    with (
        patch(
            "superset.commands.security.create.populate_roles",
            return_value=[mock_role],
        ),
        patch("superset.commands.security.create.db") as mock_db,
    ):
        mock_db.session.query.return_value = mock_query
        command.validate()

    assert command._properties["roles"] == [mock_role]
    assert command._properties["tables"] == [mock_table_1, mock_table_2]
