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
from superset.commands.security.exceptions import RLSRuleNotFoundError
from superset.commands.security.update import UpdateRLSRuleCommand


def test_update_rls_command_validate_raises_not_found_when_model_missing() -> None:
    command = UpdateRLSRuleCommand(model_id=99, data={"tables": [], "roles": []})
    with patch(
        "superset.commands.security.update.RLSDAO.find_by_id",
        return_value=None,
    ):
        with pytest.raises(RLSRuleNotFoundError):
            command.validate()


def test_update_rls_command_validate_raises_on_missing_tables() -> None:
    data = {
        "name": "updated_rule",
        "tables": [1, 2],
        "roles": [],
        "clause": "id = 1",
    }
    command = UpdateRLSRuleCommand(model_id=1, data=data)
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [MagicMock()]

    with (
        patch(
            "superset.commands.security.update.RLSDAO.find_by_id",
            return_value=MagicMock(),
        ),
        patch(
            "superset.commands.security.update.populate_roles",
            return_value=[],
        ),
        patch("superset.commands.security.update.db") as mock_db,
    ):
        mock_db.session.query.return_value = mock_query
        with pytest.raises(DatasourceNotFoundValidationError):
            command.validate()


def test_update_rls_command_validate_succeeds_when_valid() -> None:
    mock_role = MagicMock()
    mock_table = MagicMock()
    mock_model = MagicMock()

    data = {
        "name": "updated_rule",
        "tables": [1],
        "roles": [10],
        "clause": "id = 1",
    }
    command = UpdateRLSRuleCommand(model_id=1, data=data)
    mock_query = MagicMock()
    mock_query.filter.return_value.all.return_value = [mock_table]

    with (
        patch(
            "superset.commands.security.update.RLSDAO.find_by_id",
            return_value=mock_model,
        ),
        patch(
            "superset.commands.security.update.populate_roles",
            return_value=[mock_role],
        ),
        patch("superset.commands.security.update.db") as mock_db,
    ):
        mock_db.session.query.return_value = mock_query
        command.validate()

    assert command._model == mock_model
    assert command._properties["roles"] == [mock_role]
    assert command._properties["tables"] == [mock_table]
