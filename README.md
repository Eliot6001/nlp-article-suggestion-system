Project Setup and Testing Guide

This repository contains a medium-clone content suggestion system with integrated NLP capabilities. This guide covers the initial setup and testing procedures.
You have to setup an **.env**, follow **.env.example** file! 
This program assumes you are using supabase.

Project Setup (setup.sh)
The setup.sh script prepares the environment for the project, including setting up the correct Python version, installing dependencies, and generating a requirements.txt file for non-poetry environments.

Usage:

./setup.sh

What it does:

    Python Version Setup:

        Sets the local Python version to 3.10.13 using pyenv.

        Installs this version if it’s not already available.

    Poetry Installation:

        Installs the poetry package manager if it's not already installed.

    Dependency Installation:

        Installs all project dependencies specified in pyproject.toml.

    Requirements File Generation:

        Exports a requirements.txt file for systems not using poetry.

Running Tests (run_tests.sh)

The run_tests.sh script is a utility for running the project's test suite using pytest.

Usage:

./run_tests.sh

What it does:

    Activate Virtual Environment:

        Automatically activates the poetry virtual environment.

    Run All Tests:

        Runs all available tests in the tests/ directory.

    Run Module-Specific Tests:

        Separately runs tests for the article_processor and user_processor modules.

Notes:
    Ensure that pyenv and poetry are installed before running the setup script.
    The scripts assume a UNIX-like environment (e.g., Linux, macOS).
    Use chmod +x to make these scripts executable if you encounter permission errors.
