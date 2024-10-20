import os
import random
import string
import sys
import traceback
from importlib import import_module, reload
from typing import Callable

from avala_shared.logs import logger

from .attack_data import import_user_functions as import_attack_data_functions
from .config import config

is_verbose = False


tests: Callable = []
passed: str = []
failed: str = []


def test(name, dependencies=None):
    """
    Decorator for naming and defining tests and their dependencies.
    """
    if dependencies is None:
        dependencies = []

    def decorator(func):
        def wrapper(*args, **kwargs):
            global passed, failed
            if all(dep.__name__ in passed for dep in dependencies):
                try:
                    func(*args, **kwargs)
                    logger.info("✅ <green>{name}</>", name=name)
                    passed.append(func.__name__)
                except (AssertionError, Exception) as e:
                    logger.info("❗ <red>{name} -- {error}</>", name=name, error=e)
                    failed.append(func.__name__)

                    if is_verbose:
                        traceback.print_exc()
            else:
                logger.info("⏩ <yellow>{name} -- Skipped</>", name=name)
                failed.append(func.__name__)

        wrapper.__name__ = func.__name__
        tests.append(wrapper)
        return wrapper

    return decorator


def main(verbose=False):
    """
    Runs all tests and logs the results.
    """
    global is_verbose
    is_verbose = verbose

    logger.info("Running tests...")

    for test in tests:
        test()

    logger.info(
        "{icon} <green><b>{passed_count}</></> passed, <red><b>{failed_count}</></> failed.",
        icon="🎉" if not failed else "🚨",
        passed_count=len(passed),
        failed_count=len(failed),
    )

    if not failed:
        logger.info("🚀 All tests passed! You're good to go.")


@test("Import attack data functions.")
def test_attack_data_functions_import():
    fetch_json, process_json = import_attack_data_functions()
    assert fetch_json and process_json


@test("Fetch attack data.", dependencies=[test_attack_data_functions_import])
def test_attack_data_fetch_json():
    fetch_json, _ = import_attack_data_functions()
    json_or_list = fetch_json()
    assert isinstance(
        json_or_list, (dict, list)
    ), "Fetch function must return a dictionary or a list."


@test("Process attack data.", dependencies=[test_attack_data_fetch_json])
def test_attack_data_process_json():
    fetch_json, process_json = import_attack_data_functions()
    obj = process_json(fetch_json())

    assert isinstance(obj, dict), "Object is not a dictionary"

    for key, value in obj.items():
        assert isinstance(key, str), "Key '%s' is not a string" % key
        assert isinstance(value, dict), "Value for key '%s' is not a dictionary" % key

        for inner_key, inner_value in value.items():
            assert isinstance(inner_key, str), (
                "Inner key '%s' is not a string" % inner_key
            )
            assert isinstance(inner_value, list), (
                "Value for inner key '%s' is not a list" % inner_key
            )


@test("Import submitter functions.")
def test_submitter_import():
    try:
        submit = import_submitter_function("submit")
    except Exception as e:
        assert False, "Unable to load module <b>%s</>: %s" % (
            config.submitter.module,
            e,
        )

    assert submit, (
        "Required function not found within <b>%s.py</>. Please make sure the module contains <b>submit</> function."
        % config.submitter.module
    )


@test("Submit 50 fake flags.", dependencies=[test_submitter_import])
def test_flag_submission():
    submit = import_submitter_function("submit")
    prepare = import_submitter_function("prepare")
    cleanup = import_submitter_function("cleanup")

    if prepare:
        prepare()

    flags: list[str] = [gen_test_flag() for _ in range(50)]
    responses: list[tuple[str, str, str]] = []

    if config.submitter.streams:
        for flag in flags:
            response = submit(flag)
            responses.append(response)
    else:
        responses = submit(flags)

    assert responses, "No responses received."
    assert all(
        isinstance(response, tuple) and len(response) == 3 for response in responses
    ), "Each response must be a tuple of 3 elements."
    assert all(
        isinstance(item, str) for response in responses for item in response
    ), "All elements in each tuple must be strings."
    for response in responses:
        assert response[0] in flags, (
            "First string in each tuple must be a submitted flag, '%s' returned."
            % response[0]
        )
        assert response[1] in {"accepted", "rejected", "requeued"}, (
            "Second string in each tuple must be either 'accepted', 'rejected' or 'requeued'. '%s' returned."
            % response[1]
        )
    assert len(responses) == len(flags), (
        "Number of responses must match number of flags. %d flags submitted, %d responses received."
        % (
            len(flags),
            len(responses),
        )
    )

    if cleanup:
        cleanup()

    submit = import_submitter_function("submit")


def import_submitter_function(function_name: str):
    """Imports and reloads user written functions used for the actual flag submission."""
    module_name = config.submitter.module if config.submitter.module else "submitter"

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.append(cwd)

    imported_module = reload(import_module(module_name))
    return getattr(imported_module, function_name, None)


def gen_test_flag():
    return "TEST_" + "".join(
        random.choices(string.ascii_uppercase + string.digits, k=30)
    )
