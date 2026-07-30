# PatchProof for VS Code

Run PatchProof reviews from inside VS Code against your current Git changes.

## Features

- Adds a PatchProof activity bar view.
- Lets you enter the task your code change is supposed to satisfy.
- Collects the active repository's current Git diff.
- Sends the task and diff to the PatchProof backend.
- Renders the returned merge-readiness report in the sidebar.

## Backend

By default, the extension calls:

```text
http://patchproof-alb-1732344178.us-east-2.elb.amazonaws.com
```

You can override this in VS Code settings:

```json
{
  "patchproof.apiUrl": "http://localhost:8000"
}
```

## Usage

1. Open a Git repository in VS Code.
2. Make or keep local changes in the working tree.
3. Open the PatchProof view from the activity bar.
4. Enter the task description.
5. Select **Run PatchProof**.

## Local Development

```bash
npm install
npm run compile
```

Press `F5` in VS Code to launch an Extension Development Host.
