import setuptools

from session_fernet_asgi import __version__


with open("README.md", "r") as readme:
    setuptools.setup(
        name="session-fernet-asgi",
        version=__version__,
        author="v7a",
        long_description=readme.read(),
        long_description_content_type="text/markdown",
        url="https://github.com/v7a/session-fernet-asgi",
        keywords=["middleware", "asgi", "session", "fernet"],
        install_requires=["starlette >= 0.10", "cryptography >= 2.5"],
        py_modules=["session_fernet_asgi"],
        license="MIT",
        project_urls={
            "Source": "https://github.com/v7a/session-fernet-asgi",
            "Tracker": "https://github.com/v7a/session-fernet-asgi/issues",
        },
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Programming Language :: Python :: 3 :: Only",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
            "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        ],
    )
