"""Bounded, session-only reuse and numeric usage accounting; no transcripts on disk."""
from collections import OrderedDict
import hashlib
import hmac
import json
import math
import secrets
from threading import Lock
from time import perf_counter


class GroqEfficiency:
    TTL_SECONDS=300
    MAX_ENTRIES=64

    def __init__(self, *, clock=perf_counter):
        self._clock=clock
        self._lock=Lock()
        self._secret=secrets.token_bytes(32)
        self._cache=OrderedDict()
        self._cooldowns=OrderedDict()
        self._generation=0
        self._totals=dict(calls=0,failures=0,cache_hits=0,cooldown_blocks=0,
            usage_responses=0,prompt_tokens=0,completion_tokens=0,total_tokens=0,
            cached_prompt_tokens=0,latency_ms=0)

    def keys(self, credential, payload):
        # Credential-scoped opaque keys. Neither raw prompts nor credentials
        # become keys, logs, metric labels or persistent files.
        account=hmac.digest(self._secret,credential.encode(),hashlib.sha256)
        encoded=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        request=hmac.digest(account,encoded,hashlib.sha256)
        return account,request

    def lookup(self, account, key, *, reusable):
        with self._lock:
            now=self._clock()
            for expired in [k for k,(until,_) in self._cache.items() if until<=now]:
                del self._cache[expired]
            if reusable and key in self._cache:
                self._cache.move_to_end(key)
                self._totals['cache_hits']+=1
                return self._generation,self._cache[key][1],0
            delay=max(0,self._cooldowns.get(account,0)-now)
            if delay:
                self._totals['cooldown_blocks']+=1
            return self._generation,None,math.ceil(delay)

    def store(self,key,answer,generation):
        with self._lock:
            if generation!=self._generation:
                return
            self._cache[key]=(self._clock()+self.TTL_SECONDS,answer)
            self._cache.move_to_end(key)
            while len(self._cache)>self.MAX_ENTRIES:
                self._cache.popitem(last=False)

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
            self._generation+=1
            # Reload/reset must not bypass an active provider rate limit.

    def rate_limited(self,account,retry_after):
        try:
            seconds=float(retry_after)
            if not math.isfinite(seconds) or seconds<=0:
                raise ValueError
        except (TypeError,ValueError,OverflowError):
            seconds=30
        with self._lock:
            until=self._clock()+min(86400,max(1,seconds))
            self._cooldowns[account]=max(self._cooldowns.get(account,0),until)
            self._cooldowns.move_to_end(account)
            while len(self._cooldowns)>self.MAX_ENTRIES:
                self._cooldowns.popitem(last=False)

    def record(self,usage,*,failed,elapsed):
        with self._lock:
            self._totals['calls']+=1
            self._totals['failures']+=int(failed)
            self._totals['latency_ms']+=round(max(0,elapsed)*1000)
            if not isinstance(usage,dict):
                return
            names=('prompt_tokens','completion_tokens','total_tokens')
            if not all(type(usage.get(n)) is int and usage[n]>=0 for n in names):
                return
            self._totals['usage_responses']+=1
            for name in names:
                self._totals[name]+=usage[name]
            details=usage.get('prompt_tokens_details')
            cached=details.get('cached_tokens') if isinstance(details,dict) else None
            if type(cached) is int and 0<=cached<=usage['prompt_tokens']:
                self._totals['cached_prompt_tokens']+=cached

    def snapshot(self):
        with self._lock:
            return dict(self._totals)
