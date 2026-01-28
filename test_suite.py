"""
Centralized test suite for CRM Application
Runs all unit tests across different modules
"""

import sys
import unittest
from database import test_crud
from utils import test_utils
from email_handler import test_email

def run_all_tests():
    print("="*50)
    print("RUNNING CRM TEST SUITE")
    print("="*50)
    
    success = True
    
    try:
        test_utils()
    except Exception as e:
        print(f"ERROR in utils tests: {e}")
        success = False
        
    try:
        test_crud()
    except Exception as e:
        print(f"ERROR in database tests: {e}")
        success = False
        
    try:
        test_email()
    except Exception as e:
        print(f"ERROR in email tests: {e}")
        success = False
        
    print("="*50)
    if success:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("SOME TESTS FAILED. Please check the logs.")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())
