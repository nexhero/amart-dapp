#!/usr/bin/env python3

def pytest_addoption(parser):
    parser.addoption(
        "--usdc",
        action="append",
        default=[],
        help= "USDC token id"
    )
    parser.addoption(
        "--usdt",
        action="append",
        default=[],
        help= "USDT token id"
    )
    parser.addoption(
        "--appid",
        action="append",
        default=[],
        help= "Application ID"
    )
    parser.addoption(
        "--appaddr",
        action="append",
        default=[],
        help= "Application Address"
    )
    parser.addoption(
        "--al",
        action="append",
        default=[],
        help= "Application license"
    )

def pytest_generate_tests(metafunc):
    if "usdc" in metafunc.fixturenames:
        metafunc.parametrize("usdc", metafunc.config.getoption("usdc"))
    if "usdt" in metafunc.fixturenames:
        metafunc.parametrize("usdt", metafunc.config.getoption("usdt"))
    if "appid" in metafunc.fixturenames:
        metafunc.parametrize("appid", metafunc.config.getoption("appid"))
    if "appaddr" in metafunc.fixturenames:
        metafunc.parametrize("appaddr", metafunc.config.getoption("appaddr"))
    if "al" in metafunc.fixturenames:
        metafunc.parametrize("al", metafunc.config.getoption("al"))
