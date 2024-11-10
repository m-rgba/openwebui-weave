# OpenWebUI + Weave (by Weights & Biases) Input/Completion Logging

OpenWebUI function to log your inputs and completions to Weave (by Weights & Biases) for LLMOps / observability.

Implementation notes:

- [OpenWebUI](https://github.com/OpenWebUI/OpenWebUI) (open-source LLM web UI)
- [Weave](https://wandb.ai/site/weave/) (get started logging free)
    - Uses [manual call tracking](https://weave-docs.wandb.ai/guides/tracking/tracing#3-manual-call-tracking) to log inputs and completions to your Weave project.
    - Triggers the call tracking using OpenWebUI's [filter functions](https://docs.openwebui.com/tutorials/plugin/functions/) before (inlet) and after (outlet) an LLM execution.

## Installation

### 1. Setup your Weave project
- Go to https://wandb.ai/home (sign up if you don't have an account), create a new project
    - Remember your project's name, you'll need it in the next step
- Grab your API key from https://wandb.ai/settings

### 2. Run your OpenWebUI interface and install the function
- Run your OpenWebUI Docker container ([read more](https://docs.openwebui.com/getting-started/)), simplest way is to use the following command:

```bash
docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:main
```
- Visit the OpenWebUI Functions page at: http://localhost:3000/workspace/functions (assuming you used the default port and are local)
- Open `filter.py`, copy content, paste the following code into the code field and click "Install".
    - Alternatively install from the OpenWebUI gallery here: http://localhost:3000/workspace/functions/gallery
- Select the gear icon next to the function and set the `wandb_api_key` and `wandb_project_name` you copied in the first step.
    - Your API key can be found at: https://wandb.ai/settings.
    - Make sure you use `username/project_name` format for `wandb_project_name`.
- Set the function as "Global" to enable logging for all chat instances.

### 3. Profit?
- Visit https://wandb.ai/home and navigate to your project to see your logs of inputs and completions.

> [!NOTE]
> - Set the priority of the function to the highest value to have it fire (log) after any other transformations you make to your context.
> - Token counting is currently supported for OpenAI models using `tiktoken`. Non-OpenAI models will default to `gpt-4o`s token count (which will probably be close to actual token usage).
