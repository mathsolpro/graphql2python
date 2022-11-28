import os
from pathlib import Path
from typing import List, Optional, Union

from graphql import assert_name
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel
from pydantic import Field as PydanticField
from pydantic import validator

__all__ = [
    "Variable",
    "Argument",
    "Field",
    "InlineFragment",
    "Fragment",
    "Query",
    "Operation",
]


# templates setting for render of classes
TEMPLATES_FOLDER = Path(os.path.join(os.path.dirname(__file__), "templates/"))

template_env = Environment(loader=FileSystemLoader(searchpath=TEMPLATES_FOLDER))


class GraphQL2PythonQuery(BaseModel):
    """An abstract class for GraphQL query type."""

    class Config:
        smart_union = True
        extra = "forbid"
        arbitrary_types_allowed = True

    @staticmethod
    def _shift_line(text: str) -> str:
        return "\n  ".join(text.split("\n"))

    def _render_field(self, v: Union[str, 'Field', 'InlineFragment', 'Fragment']) -> str:
        if isinstance(v, str):
            return v

        if isinstance(v, Fragment):
            return f"...{v.name}"

        return self._shift_line(v.render())

    def render(self) -> str:
        raise NotImplementedError


class Variable(GraphQL2PythonQuery):
    """GraphQL variable type. See https://graphql.org/learn/queries/#variables

    Example:
        The query

        ```
        query HeroNameAndFriends($episode: Episode = JEDI) {
          hero(episode: $episode) {
            name
            friends {
              name
            }
          }
        }
        ```

        has the following variable:

        >>> Variable(name="episode", type="Episode", default="JEDI")

    """

    name: str
    type: str
    default: Optional[str] = PydanticField(default=None)

    _template: Template = template_env.get_template("variable.jinja2")

    @validator("name")
    def graphql_variable_name(cls, v: str):
        return assert_name(v)

    def render(self) -> str:
        return self._template.render(
            name=self.name,
            type=self.type,
            default=self.default
        )


class Argument(GraphQL2PythonQuery):
    """GraphQL argument type. See https://graphql.org/learn/queries/#arguments

    Example 1:
        In the query

        ```
        {
          human(id: "1000") {
            name
            height(unit: FOOT)
          }
        }
        ```

        we have two arguments

        Argument(name="id", value='"1000"')
        Argument(name="unit", value='FOOT')

    Example 2:
        In the query

        ```
        {
          q(
            filter1: {
              filter2: {
                field1: "value1"
                field2: VALUE2
              }
            }
          ) {
            ...
          }
        }
        ```

        we have the argument

        Argument(
            name="filter1",
            value=Argument(
                name="filter2",
                value=[
                    Argument(name="field1", value='"value1"'),
                    Argument(name="field2", value='VALUE2'),
                ]
            )
        )

    """

    name: str
    value: Union[str, 'Argument', List['Argument'], Variable]

    _template_key_value: Template = template_env.get_template("argument_key_value.jinja2")
    _template_key_argument: Template = template_env.get_template("argument_key_argument.jinja2")
    _template_key_variable: Template = template_env.get_template("argument_key_variable.jinja2")
    _template_key_arguments: Template = template_env.get_template("argument_key_arguments.jinja2")

    @validator("name")
    def graphql_argument_name(cls, v: str):
        return assert_name(v)

    def render(self) -> str:
        if isinstance(self.value, str):
            return self._template_key_value.render(name=self.name, value=self.value)

        if isinstance(self.value, Argument):
            return self._template_key_argument.render(
                name=self.name,
                argument=self._shift_line(self.value.render())
            )

        if isinstance(self.value, Variable):
            return self._template_key_variable.render(
                name=self.name,
                value=self.value.name
            )

        return self._template_key_arguments.render(
            name=self.name,
            arguments=[self._shift_line(argument.render()) for argument in self.value]
        )


class Field(GraphQL2PythonQuery):
    """GraphQL Field type. See https://graphql.org/learn/queries/#fields

    Example:
        In the query

        ```
        {
          query {
            field1 {
              __typename
              field2 {
                __typename
                f1
                f2
                f3
              }
            }
          }
        }
        ```

        we have the following field

        Field(
            name="field1",
            fields=[
                Field(
                    name="field2",
                    fields=["f1", "f2", "f3"],
                    typename=True
                )
            ],
            typename=True
        )

    """

    name: str
    alias: Optional[str] = PydanticField(default=None)
    arguments: List[Argument] = PydanticField(default_factory=list)
    fields: List[Union[str, 'Field', 'InlineFragment', 'Fragment']] = PydanticField(
        default_factory=list
    )
    typename: bool = PydanticField(default=False, description="add meta field __typename to sub-fields")

    _template: Template = template_env.get_template("field.jinja2")

    @validator("name")
    def graphql_field_name(cls, v: str):
        return assert_name(v)

    @validator("alias")
    def graphql_field_alias(cls, v: Optional[str]):
        if v is not None:
            return assert_name(v)
        return v

    def render(self) -> str:
        return self._template.render(
            name=self.name,
            alias=self.alias,
            arguments=[self._shift_line(argument.render()) for argument in self.arguments],
            fields=[self._render_field(field) for field in self.fields],
            typename=self.typename
        )


class InlineFragment(GraphQL2PythonQuery):
    """Inline Fragment GraphQL type. See
    https://graphql.org/learn/queries/#inline-fragments

    """

    type: str
    arguments: List[Argument] = PydanticField(default_factory=list)
    fields: List[Union[str, 'Field', 'InlineFragment', 'Fragment']] = PydanticField(
        default_factory=list
    )
    typename: bool = PydanticField(default=False, description="add meta field __typename to sub-fields")

    _template: Template = template_env.get_template("inline_fragment.jinja2")

    @validator("fields")
    def graphql_inline_fragment_fields(cls, v: List[Union[str, 'Field', 'InlineFragment', 'Fragment']]):
        if len(v) == 0:
            raise ValueError(f"empty fields for this inline fragment")
        return v

    def render(self) -> str:
        return self._template.render(
            type=self.type,
            arguments=[self._shift_line(argument.render()) for argument in self.arguments],
            fields=[self._render_field(field) for field in self.fields],
            typename=self.typename
        )


class Fragment(GraphQL2PythonQuery):
    """GraphQL fragment type. See
    https://graphql.org/learn/queries/#fragments

    """

    name: str
    type: str
    fields: List[Union[str, 'Field', 'InlineFragment', 'Fragment']] = PydanticField(
        default_factory=list
    )
    typename: bool = PydanticField(default=False, description="add meta field __typename to sub-fields")

    _template: Template = template_env.get_template("fragment.jinja2")

    @validator("name")
    def graphql_fragment_name(cls, v: str):
        return assert_name(v)

    @validator("fields")
    def graphql_fragment_fields(cls, v: List[Union[str, 'Field', 'InlineFragment', 'Fragment']]):
        if len(v) == 0:
            raise ValueError(f"empty fields for this fragment")
        return v

    def render(self) -> str:
        return self._template.render(
            name=self.name,
            type=self.type,
            fields=[self._render_field(field) for field in self.fields],
            typename=self.typename,
        )


class Query(GraphQL2PythonQuery):
    """GraphQL query type. See https://graphql.org/learn/queries/

    Example:
        In the query

        ```
        {
          human: human1000th(id: "1000") {
            name
            height
          }
        }
        ```

        we have the Query

        Query(
            name="human",
            alias="human1000th",
            arguments=[
                Argument(
                    name="id",
                    value='"1000"'
                )
            ],
            fields=["name", "height"]
        )

    """

    name: str
    alias: Optional[str] = PydanticField(default=None)
    arguments: List[Argument] = PydanticField(default_factory=list)
    typename: bool = PydanticField(default=False, description="add meta field __typename to the query")
    fields: List[Union[str, 'Field', 'InlineFragment', 'Fragment']] = PydanticField(
        default_factory=list
    )

    _template: Template = template_env.get_template("query.jinja2")

    @validator("name")
    def graphql_query_name(cls, v: str):
        return assert_name(v)

    @validator("alias")
    def graphql_alias_alias(cls, v: Optional[str]):
        if v is not None:
            return assert_name(v)
        return v

    @validator("fields")
    def graphql_query_fields(cls, v: List[Union[str, 'Field', 'InlineFragment', 'Fragment']]):
        if len(v) == 0:
            raise ValueError(f"empty fields for this query")
        return v

    def render(self) -> str:
        return self._template.render(
            name=self.name,
            alias=self.alias,
            arguments=[self._shift_line(argument.render()) for argument in self.arguments],
            typename=self.typename,
            fields=[self._render_field(field) for field in self.fields]
        )


class Operation(GraphQL2PythonQuery):
    """GraphQL operation type. See https://graphql.org/learn/queries/

    Example:
        For the query

        ```
        mutation CreateReviewForEpisode($ep: Episode!, $review: ReviewInput!) {
          createReview(episode: $ep, review: $review) {
            stars
            commentary
          }
        }
        ```

        we have

        var_ep = Variable(name="ep", type="Episode!")
        var_review = Variable(name="review", type="ReviewInput!")

        Operation(
            type="mutation",
            name="CreateReviewForEpisode",
            variables=[var_ep, var_review],
            queries=[
                Query(
                    name="createReview",
                    arguments=[
                        Argument(name="episode", value=var_ep),
                        Argument(name="review", value=var_review),
                    ],
                    fields=["stars", "commentary"]
                ),
            ],
        )

    """

    type: str = PydanticField(
        default="query",
        description="https://graphql.org/learn/queries"
    )
    name: Optional[str] = PydanticField(
        default=None,
        description="https://graphql.org/learn/queries/#operation-name"
    )
    variables: List[Variable] = PydanticField(
        default_factory=List[Variable],
        description="https://graphql.org/learn/queries/#fragments"
    )
    queries: List[Query] = PydanticField(
        default_factory=List[Query],
        description="Queries for this GraphQL operation."
    )
    fragments: List[Fragment] = PydanticField(
        default_factory=List[Fragment],
        description="https://graphql.org/learn/queries/#fragments"
    )

    _template: Template = template_env.get_template("operation.jinja2")
    _supported_types = ["query", "mutation", "subscription"]

    @validator("name")
    def graphql_operation_name(cls, v: Optional[str]):
        if v is not None:
            return assert_name(v)
        return v

    @validator("queries")
    def graphql_queries(cls, v: List[Query]):
        if len(v) == 0:
            raise ValueError(f"empty queries list for this operation")
        return v

    def render(self) -> str:
        return self._template.render(
            type=self.type,
            name=self.name,
            variables=[self._shift_line(variable.render()) for variable in self.variables],
            queries=[self._shift_line(query.render()) for query in self.queries],
            fragments=[fragment.render() for fragment in self.fragments],
        )


Variable.update_forward_refs()
Argument.update_forward_refs()
Field.update_forward_refs()
InlineFragment.update_forward_refs()
Fragment.update_forward_refs()
Query.update_forward_refs()
Operation.update_forward_refs()