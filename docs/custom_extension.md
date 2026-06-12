## Proposing an External pyRevit Extension

If your tool is too specific to be included in the main pyRevit toolset, you can still share it as an external extension so others can discover and install it.

### Steps

1. Structure your repository so the `.tab` folder is at the root.
2. Include an `extension.json` file in your repo.
3. Create a branch from the pyRevit repository.
4. Navigate to `extensions/extensions.json`.
5. Add your extension entry to the `"extensions"` list.
6. Open a pull request against the `develop` branch.

### Example Entry

A typical entry in `extensions/extensions.json` looks like this:

    {
        "builtin": "False",
        "type": "extension",
        "rocket_mode_compatible": "True",
        "name": "YourExtensionName",
        "description": "Short description of what your extension does",
        "author": "Your Name or Organization",
        "author_profile": "https://github.com/your-profile",
        "url": "https://github.com/yourname/your-extension.git",
        "website": "https://your-project-website-or-repo",
        "image": "",
        "dependencies": []
    }

### Review Process

Once you submit the PR, we’ll take a look at your extension and its metadata. If everything checks out, we’ll add it to the directory so others can easily find and use it.
