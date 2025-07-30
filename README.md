## AWS Lambda Python Runtime Interface Client

We have open-sourced a set of software packages, Runtime Interface Clients (RIC), that implement the Lambda
 [Runtime API](https://docs.aws.amazon.com/lambda/latest/dg/runtimes-api.html), allowing you to seamlessly extend your preferred
  base images to be Lambda compatible.
The Lambda Runtime Interface Client is a lightweight interface that allows your runtime to receive requests from and send requests to the Lambda service.

The Lambda Python Runtime Interface Client is vended through [pip](https://pypi.org/project/awslambdaric).
You can include this package in your preferred base image to make that base image Lambda compatible.

## Requirements
The Python Runtime Interface Client package currently supports Python versions:
 - 3.9.x up to and including 3.13.x

## Usage

### Container-Based Builds

For development or when you need to build awslambdaric from source, you can use container-based builds to ensure consistent compilation across different platforms, and native dependencies linking.

```shell script
# Build awslambdaric wheel in a Linux container
make build-container
# Or with poetry (run 'poetry install' first):
poetry run build-container

# Test with RIE using the built wheel
make test-rie
# Or with poetry:
poetry run test-rie
```

This approach builds the C++ extensions in a Linux environment, ensuring compatibility with Lambda's runtime environment regardless of your host OS.

**Note**: Running `make build` (or `poetry run build`) on non-Linux machines will not properly link the native C++ dependencies, resulting in a non-functional runtime client. Always use container-based builds for development.

### Creating a Docker Image for Lambda with the Runtime Interface Client
First step is to choose the base image to be used. The supported Linux OS distributions are:

 - Amazon Linux 2
 - Alpine
 - Debian
 - Ubuntu


Then, the Runtime Interface Client needs to be installed. We provide both wheel and source distribution.
If the OS/pip version used does not support [manylinux2014](https://www.python.org/dev/peps/pep-0599/) wheels, you will also need to install the required build dependencies.
Also, your Lambda function code needs to be copied into the image.

```dockerfile
# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Copy function code
RUN mkdir -p ${FUNCTION_DIR}
COPY app/* ${FUNCTION_DIR}

# Install the function's dependencies
RUN pip install \
    --target ${FUNCTION_DIR} \
        awslambdaric
```

The next step would be to set the `ENTRYPOINT` property of the Docker image to invoke the Runtime Interface Client and then set the `CMD` argument to specify the desired handler.

Example Dockerfile (to keep the image light we use a multi-stage build):
```dockerfile
# Define custom function directory
ARG FUNCTION_DIR="/function"

FROM public.ecr.aws/docker/library/python:buster as build-image

# Include global arg in this stage of the build
ARG FUNCTION_DIR

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Copy function code
RUN mkdir -p ${FUNCTION_DIR}
COPY app/* ${FUNCTION_DIR}

# Install the function's dependencies
RUN pip install \
    --target ${FUNCTION_DIR} \
        awslambdaric


FROM public.ecr.aws/docker/library/python:buster

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "app.handler" ]
```

Example Python handler `app.py`:
```python
def handler(event, context):
    return "Hello World!"
```

### Local Testing

To test Lambda functions with the Runtime Interface Client, use the [AWS Lambda Runtime Interface Emulator (RIE)](https://github.com/aws/aws-lambda-runtime-interface-emulator). To test your local changes with RIE (Runtime Interface Emulator):

```shell script
# Build your current code (do this when you make changes) 
# We build on a linux machine to ensure native build dependencies are met
make build-container
# Or with poetry:
poetry run build-container

# Test with RIE (fast, repeatable)
make test-rie
# Or with poetry:
poetry run test-rie

# Test the function
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"message":"test"}'
```

## Development

### Building the package
Clone this repository and run:

```shell script
make init
make build
```
### Running tests

Make sure the project is built:
```shell script
make init build
```
Then,
* to run unit tests: `make test`
* to run integration tests: `make test-integ`
* to run smoke tests: `make test-smoke`

### Troubleshooting
While running integration tests, you might encounter the Docker Hub rate limit error with the following body:
```
You have reached your pull rate limit. You may increase the limit by authenticating and upgrading: https://www.docker.com/increase-rate-limits
```
To fix the above issue, consider authenticating to a Docker Hub account by setting the Docker Hub credentials as below CodeBuild environment variables.
```shell script
DOCKERHUB_USERNAME=<dockerhub username>
DOCKERHUB_PASSWORD=<dockerhub password>
```
Recommended way is to set the Docker Hub credentials in CodeBuild job by retrieving them from AWS Secrets Manager.
## Security

If you discover a potential security issue in this project we ask that you notify AWS/Amazon Security via our [vulnerability reporting page](http://aws.amazon.com/security/vulnerability-reporting/). Please do **not** create a public github issue.

## License

This project is licensed under the Apache-2.0 License.
