#!/usr/bin/env python3
"""Debug allocation and job relationship"""

import sys
sys.path.insert(0, '/Users/rajaviswanathan/bitbucket-2021/chaosmonkey/src')

from chaosmonkey.config import Settings
from chaosmonkey.core.nomad import NomadClient
import json

def debug_job_allocation_relationship():
    """Debug job and allocation relationship"""
    print("🔍 Debugging job-allocation relationship...")
    
    settings = Settings()
    client = NomadClient(
        address=settings.nomad.address,
        region=settings.nomad.region,
        token=settings.nomad.token,
        namespace=settings.nomad.namespace,
    )
    
    # Get raw allocations to see their full structure
    try:
        allocs = client._client.allocations.get_allocations()
        print(f"📦 Found {len(allocs)} raw allocations")
        
        if allocs:
            first_alloc = allocs[0]
            print("\n🔍 First allocation full structure:")
            interesting_fields = ['Name', 'JobID', 'TaskGroup', 'ID', 'NodeID', 'ClientStatus']
            for field in interesting_fields:
                value = first_alloc.get(field, 'NOT_FOUND')
                print(f"  {field}: {value}")
        
        # Get raw jobs too
        jobs = client._client.jobs.get_jobs()
        print(f"\n🎯 Found {len(jobs)} raw jobs")
        
        if jobs:
            first_job = jobs[0]
            print("\n🔍 First job full structure:")
            interesting_fields = ['Name', 'ID', 'Type', 'Status']
            for field in interesting_fields:
                value = first_job.get(field, 'NOT_FOUND')
                print(f"  {field}: {value}")
        
        # Check if JobID in allocations matches job names/IDs
        print("\n🔗 Job-Allocation matching analysis:")
        job_names = {job.get('Name', job.get('ID')) for job in jobs}
        job_ids = {job.get('ID') for job in jobs}
        
        matching_by_job_id = 0
        matching_by_job_name = 0
        
        for alloc in allocs[:10]:  # Check first 10
            job_id = alloc.get('JobID')
            alloc_name = alloc.get('Name', '')
            
            if job_id in job_ids:
                matching_by_job_id += 1
            
            # Extract job name from allocation name (e.g., "cadvisor" from "cadvisor.cadvisor[0]")
            job_name_from_alloc = alloc_name.split('.')[0] if '.' in alloc_name else alloc_name
            if job_name_from_alloc in job_names:
                matching_by_job_name += 1
        
        print(f"  Allocations matching by JobID: {matching_by_job_id}/10")
        print(f"  Allocations matching by extracted job name: {matching_by_job_name}/10")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_job_allocation_relationship()