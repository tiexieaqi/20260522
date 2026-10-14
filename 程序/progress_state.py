def calculate_progress(statuses,scope=None):
    nums=list(scope or range(1,13)); done=sum(statuses.get(n)=='completed' for n in nums); return {'completed':done,'total':len(nums),'percent':round(done*100/len(nums)) if nums else 0,'scope_complete':done==len(nums)}
