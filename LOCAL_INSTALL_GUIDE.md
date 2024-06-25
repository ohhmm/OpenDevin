# Local Installation Guide for OpenDevin

This guide provides detailed, step-by-step instructions for installing OpenDevin locally on your system. Follow these instructions to set up the development environment, modify the cloned version of OpenDevin, and run it in a Docker container using the local clone.

## Prerequisites and System Requirements

Before you begin, ensure that your system meets the following requirements:

- **Operating System**: Linux, Mac OS, or Windows with WSL2 enabled.
- **Docker**: Version 26.0.0 or later.
- **Node.js**: Version 14.x or later.
- **npm**: Version 6.x or later.
- **Rust**: Latest stable version.
- **Conda**: Latest version.

## Step-by-Step Installation Instructions

### 1. Install Docker

Follow the official Docker installation guide for your operating system:

- [Docker for Linux](https://docs.docker.com/engine/install/)
- [Docker for Mac](https://docs.docker.com/docker-for-mac/install/)
- [Docker for Windows](https://docs.docker.com/docker-for-windows/install/)

Ensure Docker is running correctly by executing:

```bash
docker --version
```

### 2. Install Node.js and npm

Install Node.js and npm using the official installation guide:

- [Node.js and npm Installation Guide](https://nodejs.org/en/download/)

Verify the installation by running:

```bash
node --version
npm --version
```

### 3. Install Rust

Install Rust using the official installation guide:

- [Rust Installation Guide](https://www.rust-lang.org/tools/install)

Verify the installation by running:

```bash
rustc --version
```

### 4. Install Conda

Install Conda using the official installation guide:

- [Conda Installation Guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

Verify the installation by running:

```bash
conda --version
```

### 5. Clone the OpenDevin Repository

Clone the OpenDevin repository from GitHub:

```bash
git clone https://github.com/OpenDevin/OpenDevin.git
cd OpenDevin
```

### 6. Set Up the Development Environment

Install the necessary dependencies and set up the development environment for both the frontend and documentation components:

```bash
cd frontend
npm install
cd ../docs
npm install
cd ..
```

### 7. Modify the Cloned Version of OpenDevin

You can now make custom modifications to the cloned version of OpenDevin. For example, you can modify the prompts or other configurations as needed.

### 8. Run OpenDevin in a Docker Container

To run OpenDevin in a Docker container using the local clone, follow these steps:

1. Build the Docker image:

    ```bash
    docker build -t opendevin-local .
    ```

2. Run the Docker container:

    ```bash
    WORKSPACE_BASE=$(pwd)/workspace
    docker run -it \
        -e SANDBOX_USER_ID=$(id -u) \
        -e WORKSPACE_MOUNT_PATH=$WORKSPACE_BASE \
        -v $WORKSPACE_BASE:/opt/workspace_base \
        -v /var/run/docker.sock:/var/run/docker.sock \
        -p 3000:3000 \
        --add-host host.docker.internal:host-gateway \
        --name opendevin-app-local \
        opendevin-local
    ```

OpenDevin will be accessible at [http://localhost:3000](http://localhost:3000) with access to the `./workspace` directory. The workspace folder is isolated, and the rest of your system is not affected as OpenDevin runs in a secured Docker sandbox.

## Additional Resources

For more information and advanced configuration options, refer to the [OpenDevin Documentation](https://opendevin.github.io/OpenDevin/modules/usage/intro).

## Troubleshooting

If you encounter any issues during the installation or setup process, please refer to the [OpenDevin GitHub Issues](https://github.com/OpenDevin/OpenDevin/issues) for assistance or to report a problem.

## Contributing

OpenDevin is a community-driven project, and we welcome contributions from everyone. For details on how to contribute, please check the [CONTRIBUTING.md](./CONTRIBUTING.md) file.

## Join Our Community

- [Slack workspace](https://join.slack.com/t/opendevin/shared_invite/zt-2jsrl32uf-fTeeFjNyNYxqSZt5NPY3fA) - Discuss research, architecture, and future development.
- [Discord server](https://discord.gg/ESHStjSjD4) - General discussion, questions, and feedback.

Thank you for using OpenDevin!
