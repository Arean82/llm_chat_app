# test_phase8_rate_limit.py
# Automated Token Bucket Rate Limiter Verification Script

import time
import sys
import os

# Add root folder to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.services.conversation_service import TokenBucketRateLimiter

def run_rate_limit_test():
    print("==================================================")
    print("🚀 STARTING: Token Bucket Rate Limiter Unit Tests")
    print("==================================================")

    limiter = TokenBucketRateLimiter()
    tenant_id = "test_tenant_123"
    rpm_limit = 3  # 3 requests per minute

    print(f"[*] Initializing TokenBucketRateLimiter with {rpm_limit} RPM limit for user '{tenant_id}'...")

    # Step 1: Drain the bucket (3 tokens)
    print("\n[*] Step 1: Performing 3 rapid requests (within token budget)...")
    for i in range(1, 4):
        allowed = limiter.is_allowed(tenant_id, rpm_limit)
        print(f"  -> Request #{i}: {'✅ ALLOWED' if allowed else '❌ REJECTED'}")
        if not allowed:
            print("[❌ FAILURE] Expected request to be allowed, but it was rejected.")
            sys.exit(1)

    # Step 2: Request #4 should be blocked (no tokens left)
    print("\n[*] Step 2: Performing 4th rapid request (exceeding rate limit)...")
    allowed = limiter.is_allowed(tenant_id, rpm_limit)
    print(f"  -> Request #4: {'✅ ALLOWED' if allowed else '❌ REJECTED'}")
    if allowed:
        print("[❌ FAILURE] Expected request to be rejected, but it was allowed.")
        sys.exit(1)
    else:
        print("  -> Correctly rejected with 429 logic (bucket empty).")

    # Step 3: Test Dynamic Config Refresh
    print("\n[*] Step 3: Upgrading limit dynamically to 10 RPM...")
    new_rpm_limit = 10
    allowed = limiter.is_allowed(tenant_id, new_rpm_limit)
    print(f"  -> Immediate Request under upgraded limit: {'✅ ALLOWED' if allowed else '❌ REJECTED'}")
    if not allowed:
        print("[❌ FAILURE] Expected upgraded request to be allowed.")
        sys.exit(1)

    # Step 4: Test Token Replenishment over Time
    print("\n[*] Step 4: Downgrading to 3 RPM and waiting 20 seconds for token replenishment...")
    limiter.is_allowed(tenant_id, 3) # Drain any remainder to 0 tokens
    # Ensure bucket is fully depleted at 3 RPM
    while limiter.is_allowed(tenant_id, 3):
        pass
    
    print("  -> Waiting 21 seconds...")
    time.sleep(21)
    
    # 20 seconds at 3 RPM should replenish 1 token (3 tokens / 60 seconds = 0.05 tokens/sec * 20 sec = 1 token)
    allowed = limiter.is_allowed(tenant_id, 3)
    print(f"  -> Request after 21s wait: {'✅ ALLOWED' if allowed else '❌ REJECTED'}")
    if not allowed:
        print("[❌ FAILURE] Token replenishment failed after waiting 21 seconds.")
        sys.exit(1)
    
    allowed_again = limiter.is_allowed(tenant_id, 3)
    print(f"  -> Subsequent immediate request: {'✅ ALLOWED' if allowed else '❌ REJECTED'}")
    if allowed_again:
        print("[❌ FAILURE] Expected second request to be rejected since only 1 token replenished.")
        sys.exit(1)
    else:
        print("  -> Correctly allowed only 1 replenished token, blocked subsequent requests.")

    print("\n==================================================")
    print("🎉 SUCCESS: Token Bucket Rate Limiter passes all tests!")
    print("==================================================")

if __name__ == "__main__":
    run_rate_limit_test()
