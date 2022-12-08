# GRAPHQL2PYTHON

[![Build](https://img.shields.io/github/workflow/status/denisart/graphql2python/Code%20checking)](https://github.com/denisart/graphql2python/actions)
[![tag](https://img.shields.io/github/v/tag/denisart/graphql2python)](https://github.com/denisart/graphql2python)
[![last-commit](https://img.shields.io/github/last-commit/denisart/graphql2python/master)](https://github.com/denisart/graphql2python)
[![license](https://img.shields.io/github/license/denisart/graphql2python)](https://github.com/denisart/graphql2python/blob/master/LICENSE)

graphql2python is a tool that generates python code out of your GraphQL schema.
If you are using python as GraphQL client you can to generate GraphQL queries and
pydantic data-model with graphql2python.

graphql2python has the following tools for your python GraphQL client:

- python classes for generate of GraphQL queries;
- the function for generation of pydantic data-model by your GraphQL schema;
- ... (in future releases);

The special example for [gql](https://gql.readthedocs.io/en/latest/index.html) users [here](https://github.com/denisart/graphql2python/blob/master/docs/source/gql.rst).

## Quickstart

Install with pip

```bash
pip install graphql2python
```

Create the following file

```yaml
# graphql2python.yaml
schema: ./schema.graphql
output: ./model.py
```

and run the following command

```bash
graphql2python render --config ./graphql2python.yaml
```

See the documentation for all the possibilities (
while it is `docs/source/`).