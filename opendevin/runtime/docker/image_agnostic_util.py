import tempfile

import docker

from opendevin.core.logger import opendevin_logger as logger


def generate_dockerfile_content(base_image: str) -> str:
    """
    Generate the Dockerfile content for the agnostic sandbox image based on user-provided base image.

    NOTE: This is only tested on debian yet.
    """
    # FIXME: Remove the requirement of ssh in future version
    dockerfile_content = (
        f'FROM {base_image}\n'
        'RUN apt update && apt install -y openssh-server wget sudo\n'
        'RUN mkdir -p -m0755 /var/run/sshd\n'
        'RUN mkdir -p /opendevin && mkdir -p /opendevin/logs && chmod 777 /opendevin/logs\n'
        'RUN echo "" > /opendevin/bash.bashrc\n'
        'RUN if [ ! -d /opendevin/miniforge3 ]; then \\\n'
        '        wget --progress=bar:force -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh" && \\\n'
        '        bash Miniforge3.sh -b -p /opendevin/miniforge3 && \\\n'
        '        chmod -R g+w /opendevin/miniforge3 && \\\n'
        '        bash -c ". /opendevin/miniforge3/etc/profile.d/conda.sh && conda config --set changeps1 False && conda config --append channels conda-forge"; \\\n'
        '    fi\n'
        'RUN /opendevin/miniforge3/bin/pip install --upgrade pip\n'
        'RUN /opendevin/miniforge3/bin/pip install jupyterlab notebook jupyter_kernel_gateway flake8\n'
        'RUN /opendevin/miniforge3/bin/pip install python-docx PyPDF2 python-pptx pylatexenc openai\n'
    ).strip()
    return dockerfile_content


def _build_sandbox_image(
    base_image: str, target_image_name: str, docker_client: docker.DockerClient
):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            dockerfile_content = generate_dockerfile_content(base_image)
            logger.info(f'Building agnostic sandbox image: {target_image_name}')
            logger.info(
                (
                    f'===== Dockerfile content =====\n'
                    f'{dockerfile_content}\n'
                    f'==============================='
                )
            )
            with open(f'{temp_dir}/Dockerfile', 'w') as file:
                file.write(dockerfile_content)

            api_client = docker_client.api
            build_logs = api_client.build(path=temp_dir, tag=target_image_name, rm=True, decode=True)

            for log in build_logs:
                if 'stream' in log:
                    print(log['stream'].strip())
                elif 'error' in log:
                    logger.error(log['error'].strip())
                else:
                    logger.info(str(log))

        logger.info(f'Image {target_image_name} built successfully')
    except docker.errors.BuildError as e:
        logger.error(f'Sandbox image build failed: {e}')
        raise e
    except Exception as e:
        logger.error(f'An error occurred during sandbox image build: {e}')
        raise e


def _get_new_image_name(base_image: str) -> str:
    if ':' not in base_image:
        base_image = base_image + ':latest'

    [repo, tag] = base_image.split(':')
    repo = repo.replace('/', '___')
    return f'od_sandbox:{repo}__{tag}'


def get_od_sandbox_image(base_image: str, docker_client: docker.DockerClient) -> str:
    """Return the sandbox image name based on user-provided base image.

    The returned sandbox image is assumed to contains all the required dependencies for OpenDevin.
    If the sandbox image is not found, it will be built.
    """
    # OpenDevin's offcial sandbox already contains the required dependencies for OpenDevin.
    if 'ghcr.io/opendevin/sandbox' in base_image:
        return base_image

    new_image_name = _get_new_image_name(base_image)

    # Detect if the sandbox image is built
    images = docker_client.images.list()
    for image in images:
        if new_image_name in image.tags:
            logger.info('Found existing od_sandbox image, reuse:' + new_image_name)
            return new_image_name

    # If the sandbox image is not found, build it
    logger.info(
        f'od_sandbox image is not found for {base_image}, will build: {new_image_name}'
    )
    _build_sandbox_image(base_image, new_image_name, docker_client)
    return new_image_name
