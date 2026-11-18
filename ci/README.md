# Offline check template

`offline-checks.yml` runs unit tests, compilation, public report generation,
publication-artifact validation and whitespace checks without licensed sources.

It is not installed as an active GitHub Actions workflow. GitHub rejected the
initial upload because the publication credential lacks `workflow` scope. With
an appropriately authorized credential, copy this file to
`.github/workflows/tests.yml` and push it. No repository visibility or token
permissions were changed during publication.
