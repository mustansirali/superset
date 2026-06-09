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

from superset.temporary_cache.utils import cache_key, SEPARATOR


def test_cache_key_single_arg() -> None:
    assert cache_key("dashboard") == "dashboard"


def test_cache_key_multiple_args() -> None:
    assert cache_key("dashboard", 1, "tab_1") == "dashboard;1;tab_1"


def test_cache_key_integer_args() -> None:
    assert cache_key(1, 2, 3) == "1;2;3"


def test_cache_key_empty_string_arg() -> None:
    assert cache_key("", "value") == ";value"


def test_cache_key_uses_separator_constant() -> None:
    result = cache_key("a", "b")
    assert SEPARATOR in result
    assert result == f"a{SEPARATOR}b"


@pytest.mark.parametrize(
    "args,expected",
    [
        (("key",), "key"),
        ((1, 2), "1;2"),
        (("a", "b", "c"), "a;b;c"),
        ((None,), "None"),
    ],
)
def test_cache_key_parametrized(
    args: tuple[str | int | None, ...], expected: str
) -> None:
    assert cache_key(*args) == expected
