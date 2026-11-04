# Code review guidelines

When reviewing pull requests in this repository, focus on the following points.

## Consistency
- New code should follow the standards, conventions and patterns already used in the rest of the repository (naming, structure, file layout, error handling, configuration handling).
- Prefer existing abstractions and utilities over introducing new styles or approaches.

## Code duplication
- Avoid code duplication. Every piece of functionality should be implemented only once.
- Shared functionality should be factored out and reused, instead of being copied or re-implemented in a slightly different way.
- Flag new code that re-implements something that already exists in the repository.

## Avoid badly designed or written code
- Flag code that is clearly badly structured, for example:
  - files that are too large
  - functions that are too long
  - functions with too many arguments
  - classes with too many members
- Do not apply overly strict rules here. Only raise issues that are obvious.

## Documentation
- Documentation is not required for every class and function.
- Where documentation or comments are provided, they must be accurate, complete and understandable.
- Flag documentation that is outdated, misleading, incomplete or hard to understand, for example docstrings that no longer match the code's behavior or parameters.
