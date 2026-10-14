import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from structured_schema import prepare_codex_output_schema, validate_codex_schema_compatibility
from stage03_manager import ASSET_PLAN_SCHEMA
from stage04_manager import PROMPT_SCHEMA
from stage05_manager import STORYBOARD_SCHEMA
from stage06_manager import PLAN_SCHEMA as S06
from stage07_manager import PLAN_SCHEMA as S07
from stage08_manager import PLAN_SCHEMA as S08
from stage09_manager import PLAN_SCHEMA as S09

def main():
    schemas={'stage03':ASSET_PLAN_SCHEMA,'stage04':PROMPT_SCHEMA,'stage05':STORYBOARD_SCHEMA,'stage06':S06,'stage07':S07,'stage08':S08,'stage09':S09}
    report=[]
    for name,s in schemas.items():
        before=validate_codex_schema_compatibility(s); fixed=prepare_codex_output_schema(s); after=validate_codex_schema_compatibility(fixed); report.append({'stage':name,'schema_name':name,'valid_before':not before,'issues_before':before,'fix_applied':bool(before),'valid_after':not after})
        assert not after, (name,after)
    bad={'type':'array','items':{'type':'object','properties':{'name':{'type':'string'}},'required':['name']}}
    assert any(x['type']=='missing_additionalProperties_false' for x in validate_codex_schema_compatibility(bad)); assert not validate_codex_schema_compatibility(prepare_codex_output_schema(bad))
    Path('structured_schema_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print('structured_schema_preflight_test：全部通过')
if __name__=='__main__': main()
