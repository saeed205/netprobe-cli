**What changed**

**Why**

If you made a non-obvious choice, explain the reasoning here - that is the part
nobody can reconstruct from the diff later.

**Checklist**

- [ ] `python -m unittest discover -s tests` passes
- [ ] `ruff check .` is clean
- [ ] New behaviour has tests, and boundary cases are covered
- [ ] Exit status follows the convention (`0` ok, `1` check failed, `2` usage)
- [ ] README updated if a user-visible flag or output changed
