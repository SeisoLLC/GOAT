#!/usr/bin/env python3
"""
Test salacious_code_reviews/config.py
"""

import argparse
import logging

from salacious_code_reviews import config


def test_get_args_config(mocker):
    """Test get_args_config()"""
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(loglevel=30),
        autospec=True,
    )

    # Validate the return type
    assert isinstance(config.get_args_config(), dict)


def test_setup_logging(mocker):
    """Test setup_logging()"""
    mocker.patch(
        "argparse.ArgumentParser.parse_args",
        return_value=argparse.Namespace(loglevel=30),
        autospec=True,
    )

    # Validate the return type
    assert isinstance(config.setup_logging(), logging.Logger)


def test_create_arg_parser():
    """Test create_arg_parser()"""
    # Validate the return type
    assert isinstance(config.create_arg_parser(), argparse.ArgumentParser)
