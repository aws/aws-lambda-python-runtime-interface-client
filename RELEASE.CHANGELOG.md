### August 22, 2023

`2.0.6`:

- Add structured logging implementation ([#101](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/101))

### August 16, 2023

`2.0.5`:

- Add support for Python3.11. ([#103](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/103))
- Add support for Python3.10. ([#102](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/102))
- Emit multi-line logs with timestamps.([#92](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/92))
- Remove importlib-metadata dependency.([#83](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/83))

### May 25, 2022

`2.0.4`:

- Update os distro and runtime versions in compatibility tests, source base images from Amazon ECR Public ([#80](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/80))
- Improve error output for missing handler ([#70](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/70))
- Update curl to 7.83.1 ([#79](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/79))

### May 4, 2022

`2.0.3`:

- Add changelog ([#75](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/75))
- Fix curl download url ([#74](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/74))
- Update curl to 7.83.0 ([#72](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/72))

### Apr 7, 2022

`2.0.2`:

- Add leading zeros to the milliseconds part of a log timestamp ([#13](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/13))
- Use the raw fd directly rather than opening the fd pseudo file ([#56](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/56))

### Jan 4, 2022

`2.0.1`:

- Add '--no-same-owner' option to all scripts tar commands ([#37](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/37))

### Sep 29, 2021

`2.0.0`:

- Add arm64 architecture support ([#59](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/59))
- Update Curl to 7.78.0 ([#52](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/52))

### Aug 23, 2021

`1.2.2`:

- Remove importlib.metadata dependency ([#55](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/55))

### Aug 20, 2021

`1.2.1`:

- Remove logging for handler directory, as its adding un-necessary cloudwatch cost ([#51](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/51))

### Jun 28, 2021

`1.2.0`:

- Move the `/` to `.` replacement only for import_module call ([#47](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/47))
- Add support for `/` in handler name ([#45](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/45))
- Add requestId in error response ([#40](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/40))

### Jun 9, 2021

`1.1.1`:

- Update Curl version to 7.77.0 ([#33](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/35))

### May 28, 2021

`1.1.0`:

- Release GIL when polling Runtime API for next invocation ([#33](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/33))
- Use importlib instead of deprecated imp module ([#28](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/28))
- Rename test directory ([#21](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/21))
- Revise fetching latest patch version of python ([#9](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/9))
- Update README.md examples: remove period from curl command ([#7](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/7))
- Add 'docker login' to fix pull rate limit issue ([#5](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/5))
- Include GitHub action on push and pr ([#3](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/3))
- Use Python 3.6 for Black ([#2](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/2))
- Tidy up setup.py ([#1](https://github.com/aws/aws-lambda-python-runtime-interface-client/pull/1))

### Dec 01, 2020

`1.0.0`:

- Initial release of AWS Lambda Python Runtime Interface Client
