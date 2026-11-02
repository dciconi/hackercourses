# Data and content licensing

The repository mixes three kinds of material. They are licensed differently.

## 1. Code and original artwork: MIT

Everything in `pipeline/`, `tests/`, the site's HTML templates, JavaScript and CSS, and the original
artwork (`site/img/topics/`, `site/img/og/`, the logo mark) is licensed under the MIT License in
[`LICENSE`](LICENSE).

## 2. Data this project generated: CC BY 4.0

The course catalog (merged course names and providers), rankings, scores, badges, topics, course
summaries, "why people recommend it" lines, level/cost/format facets, tags and stance labels were
produced by this project's pipeline. They are licensed under
[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/).
Credit "Hacker Courses (hackercourses.com)" with a link.

## 3. Third-party content: not licensed by this project

- **Hacker News comments.** Comment text quoted in `site/course/*/index.html` remains the property of
  its authors and is not covered by either license above. It is shown with attribution and a link to
  the original. Authors can ask for removal by
  [opening an issue](https://github.com/dciconi/hackercourses/issues/new?title=Removal%20request&labels=removal).
- **Source datasets.** Comments were obtained from `nixiesearch/hackernews-comments` (Apache-2.0) and
  `open-index/hacker-news` (ODC-By 1.0), plus the HN Search API by Algolia; see [`NOTICE`](NOTICE).
- **Course images.** Preview images are loaded from each course provider's own site and are not stored
  in this repository. They belong to their providers.
- **Course names** and provider names are the trademarks of their owners.

## Name and logo

These licenses do not grant rights to the "Hacker Courses" name or logo. Forks are welcome under the
licenses above, but please use a different name.

*This summary is not legal advice.*
