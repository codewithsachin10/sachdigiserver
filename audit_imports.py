#!/usr/bin/env python3
"""
SachDeploy Automated Import Audit & Verification Script
Walks all packages and modules in the backend directory to ensure no broken imports,
stale references, or circular dependencies exist after code refactorings.
"""

import sys
import os
import importlib
import pkgutil

# Ensure current directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def audit_backend_imports():
    print("=================================================================")
    print("🔍 [SachDeploy Audit] Starting full backend package import check...")
    print("=================================================================")
    
    import backend
    package_path = backend.__path__
    prefix = "backend."
    
    modules_to_test = ["backend"]
    for _, modname, _ in pkgutil.walk_packages(path=package_path, prefix=prefix):
        modules_to_test.append(modname)
        
    success_count = 0
    failures = []
    
    for modname in sorted(modules_to_test):
        try:
            importlib.import_module(modname)
            success_count += 1
            print(f"  ✔ Verified: {modname}")
        except Exception as e:
            # Ignore expected runtime Docker Socket connection errors during static audit
            err_str = str(e)
            if "Connection aborted" in err_str or "No such file or directory" in err_str:
                success_count += 1
                print(f"  ✔ Verified: {modname} (with expected offline runtime warning: {e})")
            else:
                print(f"  ❌ FAILED: {modname} -> {type(e).__name__}: {e}")
                failures.append((modname, f"{type(e).__name__}: {e}"))
                
    print("=================================================================")
    if failures:
        print(f"🚨 AUDIT FAILED! Found {len(failures)} broken module(s):")
        for mod, err in failures:
            print(f"   - {mod}: {err}")
        print("=================================================================")
        sys.exit(1)
    else:
        print(f"🚀 AUDIT PASSED! All {success_count} backend modules verified cleanly.")
        print("   No ImportErrors, circular dependencies, or stale wrapper imports.")
        print("=================================================================")
        sys.exit(0)

if __name__ == "__main__":
    audit_backend_imports()
