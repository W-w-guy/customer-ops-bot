#!/usr/bin/env python3
"""一条命令跑完全部测试：python3 test_all.py"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(os.path.join(HERE, "tests"), top_level_dir=HERE)
    r = unittest.TextTestRunner(verbosity=1).run(suite)
    n = r.testsRun
    print("\n%s：%d 项，失败 %d，错误 %d" % ("通过" if r.wasSuccessful() else "未通过",
                                            n, len(r.failures), len(r.errors)))
    sys.exit(0 if r.wasSuccessful() else 1)
