"""Codex Structured Outputs strict-schema normalization and audit."""
from __future__ import annotations
import copy

def prepare_codex_output_schema(schema: dict) -> dict:
    out=copy.deepcopy(schema)
    def walk(node, path=''):
        if not isinstance(node, dict): return
        if node.get('type') == 'object':
            node['additionalProperties']=False
            props=node.get('properties',{})
            if isinstance(props,dict):
                node['required']=list(props.keys())
                for k,v in props.items(): walk(v, f'{path}.properties.{k}' if path else f'properties.{k}')
        if node.get('type') == 'array' and isinstance(node.get('items'),dict): walk(node['items'], f'{path}.items' if path else 'items')
        for key in ('$defs','definitions'):
            if isinstance(node.get(key),dict):
                for k,v in node[key].items(): walk(v, f'{path}.{key}.{k}' if path else f'{key}.{k}')
    walk(out)
    return out

def validate_codex_schema_compatibility(schema: dict) -> list[dict]:
    issues=[]
    def walk(node,path=''):
        if not isinstance(node,dict):
            issues.append({'path':path,'type':'invalid_node'}); return
        if node.get('type')=='object':
            if node.get('additionalProperties') is not False: issues.append({'path':path or '$','type':'missing_additionalProperties_false'})
            props=node.get('properties',{})
            req=node.get('required',[])
            if not isinstance(props,dict): issues.append({'path':path,'type':'invalid_properties'})
            elif set(req)!=set(props): issues.append({'path':path,'type':'required_mismatch','required':req,'properties':list(props)})
            for k,v in props.items(): walk(v,f'{path}.properties.{k}' if path else f'properties.{k}')
        if node.get('type')=='array' and isinstance(node.get('items'),dict): walk(node['items'],f'{path}.items' if path else 'items')
        for key in ('$defs','definitions'):
            for k,v in (node.get(key) or {}).items(): walk(v,f'{path}.{key}.{k}' if path else f'{key}.{k}')
    walk(schema)
    return issues
