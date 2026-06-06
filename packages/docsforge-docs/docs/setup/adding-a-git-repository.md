# Adding a git repository

Link your documentation to its source repository. This adds an "Edit this page" button and shows the repository name in the header.

## Basic configuration

``` yaml
repo_name: username/repo
repo_url: https://github.com/username/repo
```

## Edit button

Enable the "Edit this page" button:

``` yaml
theme:
  features:
    - content.action.edit
```

This adds a pencil icon that links directly to the source file on GitHub (or your provider).

## View source button

Enable the "View source" button alongside edit:

``` yaml
theme:
  features:
    - content.action.edit
    - content.action.view
```

## Custom provider

DocsForge supports any Git provider that follows the GitHub URL pattern:

``` yaml
repo_url: https://gitlab.com/username/repo
# or
repo_url: https://bitbucket.org/username/repo
# or
repo_url: https://gitea.example.com/username/repo
```

## Repository icon

The repository icon is shown in the header. It's automatically determined from the URL:

- `github.com` → GitHub icon
- `gitlab.com` → GitLab icon
- `bitbucket.org` → Bitbucket icon

## Custom edit path

If your docs live in a subdirectory of the repository:

``` yaml
edit_uri: edit/main/docs/
```

The full edit URL becomes: `https://github.com/username/repo/edit/main/docs/page.md`

## Complete example

``` yaml
repo_name: myproject/docs
repo_url: https://github.com/myproject/docs
edit_uri: edit/main/docs/

theme:
  features:
    - content.action.edit
    - content.action.view
```

## Next steps

- [Publishing your site](../publishing-your-site.md)
- [Setup overview](index.md)

## Troubleshooting

### Edit button 404s

If the edit button leads to a 404 page:

1. Check `edit_uri` matches your repository structure
2. For GitHub: `edit_uri: edit/main/docs/` (branch + docs folder)
3. For GitLab: `edit_uri: edit/main/docs/-/blob/` (different path format)
4. Ensure the repository is public (or the user has access)

### Wrong icon showing

The repository icon is auto-detected from the URL. If the wrong icon appears:

1. Check `repo_url` is correct
2. For custom icons, set `icon.repo` in `docsforge.yml`:
   ```yaml
   icon:
     repo: fontawesome/brands/github
   ```

## Private repositories

For private repositories, the edit button still works for users with access:

``` yaml
repo_url: https://github.com/mycompany/private-docs
```

Users who don't have access will see a 404 when clicking the edit button. Consider adding a note about this in your documentation.
