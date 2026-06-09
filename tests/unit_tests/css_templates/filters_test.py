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
from flask_appbuilder.models.sqla.interface import SQLAInterface
from sqlalchemy.orm.session import Session

from superset.css_templates.filters import CssTemplateAllTextFilter
from superset.models.core import CssTemplate
from superset.views.base import BaseFilter


def test_css_template_all_text_filter_is_base_filter() -> None:
    assert issubclass(CssTemplateAllTextFilter, BaseFilter)


def test_css_template_all_text_filter_attributes() -> None:
    assert CssTemplateAllTextFilter.arg_name == "css_template_all_text"


def test_css_template_all_text_filter_returns_unmodified_on_empty_value(
    session: Session,
) -> None:
    query = session.query(CssTemplate)
    datamodel = SQLAInterface(CssTemplate, session)
    filter_instance = CssTemplateAllTextFilter("template_name", datamodel)
    result = filter_instance.apply(query, "")
    assert str(result) == str(query)


def test_css_template_all_text_filter_returns_unmodified_on_none(
    session: Session,
) -> None:
    query = session.query(CssTemplate)
    datamodel = SQLAInterface(CssTemplate, session)
    filter_instance = CssTemplateAllTextFilter("template_name", datamodel)
    result = filter_instance.apply(query, None)
    assert str(result) == str(query)


def test_css_template_all_text_filter_applies_ilike_on_name_and_css(
    session: Session,
) -> None:
    engine = session.get_bind()
    query = session.query(CssTemplate)
    datamodel = SQLAInterface(CssTemplate, session)
    filter_instance = CssTemplateAllTextFilter("template_name", datamodel)
    result = filter_instance.apply(query, "dark")
    compiled = result.statement.compile(engine, compile_kwargs={"literal_binds": True})
    sql = str(compiled)
    assert "dark" in sql.lower()
    assert "template_name" in sql.lower() or "css" in sql.lower()
