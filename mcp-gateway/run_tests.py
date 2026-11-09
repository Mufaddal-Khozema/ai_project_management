import os
import sys
import traceback

os.environ["TESTING"] = "true"

def run_all():

    passed = 0
    failed = 0

    import tests.test_guardrails as tg
    import tests.test_fallback as tf
    import tests.test_api as ta
    import tests.test_jira_plugin as tj

    modules = [tg, tf, ta, tj]

    for mod in modules:
        for name in dir(mod):
            if name.startswith("test_"):
                fn = getattr(mod, name)
                if callable(fn):
                    try:
                        print(f"RUNNING: {mod.__name__}.{name}...", flush=True)
                        if name == "test_supported_tools":
                            from plugins.pm_jira import JiraPlugin
                            fn(JiraPlugin())
                        elif name.startswith("test_execute_jira"):
                            from plugins.pm_jira import JiraPlugin
                            fn(JiraPlugin())
                        else:
                            fn()
                        print(f"PASSED: {mod.__name__}.{name}", flush=True)
                        passed += 1
                    except Exception as e:
                        print(f"FAILED: {mod.__name__}.{name}: {e}", flush=True)
                        traceback.print_exc()
                        failed += 1


    print(f"\n==========================================")
    print(f"TOTAL: {passed + failed} | PASSED: {passed} | FAILED: {failed}")
    print(f"==========================================")
    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
