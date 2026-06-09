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

from superset.commands.css.delete import DeleteCssTemplateCommand
from superset.commands.css.exceptions import CssTemplateNotFoundError


def test_delete_css_template_command_validate_raises_not_found_when_empty() -> None:
    command = DeleteCssTemplateCommand([1, 2, 3])
    with patch(
        "superset.commands.css.delete.CssTemplateDAO.find_by_ids",
        return_value=[],
    ):
        with pytest.raises(CssTemplateNotFoundError):
            command.validate()


def test_delete_css_template_command_validate_raises_not_found_on_partial_match() -> (
    None
):
    mock_model = MagicMock()
    command = DeleteCssTemplateCommand([1, 2, 3])
    with patch(
        "superset.commands.css.delete.CssTemplateDAO.find_by_ids",
        return_value=[mock_model],
    ):
        with pytest.raises(CssTemplateNotFoundError):
            command.validate()


def test_delete_css_template_command_validate_succeeds_on_full_match() -> None:
    mock_models = [MagicMock(), MagicMock()]
    command = DeleteCssTemplateCommand([1, 2])
    with patch(
        "superset.commands.css.delete.CssTemplateDAO.find_by_ids",
        return_value=mock_models,
    ):
        command.validate()
        assert command._models == mock_models


def test_delete_css_template_command_validate_raises_not_found_on_none() -> None:
    command = DeleteCssTemplateCommand([1])
    with patch(
        "superset.commands.css.delete.CssTemplateDAO.find_by_ids",
        return_value=None,
    ):
        with pytest.raises(CssTemplateNotFoundError):
            command.validate()
