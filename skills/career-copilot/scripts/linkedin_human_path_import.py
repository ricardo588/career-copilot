#!/usr/bin/env python3
"""Read a private LinkedIn connections export and emit Human Path clues to stdout."""
from __future__ import annotations
import argparse,csv,io,json,os,stat
from pathlib import Path
from typing import Any

class BoundaryError(ValueError): pass

def absolute(raw:str)->Path:
    path=Path(os.path.abspath(os.path.expanduser(raw)))
    for alias in (Path("/tmp"),Path("/var")):
        if path==alias or alias in path.parents:return alias.resolve()/path.relative_to(alias)
    return path
def check(path:Path,workspace:Path,label:str)->Path:
    repo=Path(__file__).resolve().parents[3]
    try: path.relative_to(workspace)
    except ValueError as e: raise BoundaryError(f"{label} must be within the private workspace") from e
    if workspace==repo or repo in workspace.parents or workspace in repo.parents: raise BoundaryError("workspace cannot overlap distribution")
    for ancestor in (path,*path.parents):
        if ancestor.is_symlink(): raise BoundaryError(f"{label} cannot be beneath a symlink")
        if (ancestor/".git").exists(): raise BoundaryError(f"{label} cannot be beneath a Git repository")
    return path

def open_chain(path:Path)->tuple[int,list[int]]:
    flags=os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0)
    root=os.open("/",flags); current=root; chain=[root]
    try:
        for part in path.parts[1:]:
            current=os.open(part,flags,dir_fd=current);chain.append(current)
        return current,chain
    except Exception:
        for descriptor in reversed(chain):os.close(descriptor)
        raise

def ensure_fd_not_git(descriptor:int)->None:
    try:os.stat(".git",dir_fd=descriptor,follow_symlinks=False)
    except FileNotFoundError:return
    raise BoundaryError("input cannot be beneath a Git repository")

def ensure_not_git(chain:list[int])->None:
    for descriptor in chain:ensure_fd_not_git(descriptor)

def open_workspace(raw:str)->tuple[Path,int,list[int]]:
    workspace=absolute(raw); check(workspace,workspace,"workspace")
    fd,chain=open_chain(workspace);ensure_not_git(chain)
    return workspace,fd,chain
def read_private(workspace:Path,fd:int,path:Path,label:str)->bytes:
    relative=path.relative_to(workspace); parent=os.dup(fd)
    try:
        ensure_fd_not_git(parent)
        for part in relative.parts[:-1]:
            nxt=os.open(part,os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|getattr(os,"O_NOFOLLOW",0),dir_fd=parent);os.close(parent);parent=nxt;ensure_fd_not_git(parent)
        filefd=os.open(relative.name,os.O_RDONLY|getattr(os,"O_NOFOLLOW",0),dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(filefd).st_mode): raise BoundaryError(f"{label} must be regular")
            with os.fdopen(filefd,"rb") as h: filefd=-1;return h.read()
        finally:
            if filefd>=0:os.close(filefd)
    finally: os.close(parent)
def text(x:Any)->str:return x.strip() if isinstance(x,str) else ""
def identity(row:dict[str,str])->str:return (text(row.get("First Name"))+" "+text(row.get("Last Name"))).strip().casefold()
def artifact(export:bytes,vacancy:bytes)->dict[str,Any]:
    reader=csv.DictReader(io.StringIO(export.decode("utf-8-sig")),strict=True); allowed={"First Name","Last Name","Company","Position","Connected On"}
    if not reader.fieldnames or not {"First Name","Last Name","Company"}.issubset(reader.fieldnames):raise BoundaryError("export requires First Name, Last Name and Company headers")
    if len(reader.fieldnames)!=len(set(reader.fieldnames)) or set(reader.fieldnames)-allowed:raise BoundaryError("export has duplicate or unsupported headers")
    rows=list(reader)
    if any(None in row for row in rows):raise BoundaryError("export contains rows with unsupported extra fields")
    if any(any(not text(row.get(field)) for field in ("First Name","Last Name","Company")) for row in rows):raise BoundaryError("export rows require all required fields")
    data=json.loads(vacancy.decode("utf-8"))
    if not isinstance(data,dict):raise BoundaryError("vacancy must be a JSON mapping")
    company=text(data.get("company"))
    if not company:raise BoundaryError("vacancy requires company")
    raw_recruiter=data.get("recruiter")
    if raw_recruiter is None:name=""
    elif not isinstance(raw_recruiter,dict) or not isinstance(raw_recruiter.get("name"),str) or not text(raw_recruiter["name"]):raise BoundaryError("recruiter must be a mapping with a non-empty name")
    else:name=text(raw_recruiter["name"])
    rows=[r for r in rows if text(r.get("Company")).casefold()==company.casefold() and identity(r)]
    if name:rows=[r for r in rows if identity(r)==name.casefold()]
    matches=[{"name":(text(r.get("First Name"))+" "+text(r.get("Last Name"))).strip(),"declared_company":text(r.get("Company")),"declared_role":text(r.get("Position")),"discovery_state":"export_match_found","identity_state":"needs_identity_review","current_employment":"unverified","authorization":"not_granted","relationship":"candidate_owned_contact","source":"linkedin_connections_export"} for r in rows]
    return {"schema_version":1,"matches":matches,"ambiguities":["manual_review_required"] if matches else [],"safety":{"external_actions":0,"network_requests":0,"input_mutated":False}}
def run(argv:list[str]|None=None)->str:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--workspace",required=True);p.add_argument("--export",required=True);p.add_argument("--vacancy",required=True);a=p.parse_args(argv)
    workspace,fd,chain=open_workspace(a.workspace)
    try:
        export=check(absolute(a.export),workspace,"export");vacancy=check(absolute(a.vacancy),workspace,"vacancy")
        ensure_not_git(chain)
        return json.dumps(artifact(read_private(workspace,fd,export,"export"),read_private(workspace,fd,vacancy,"vacancy")),ensure_ascii=False)
    finally:
        for descriptor in reversed(chain):os.close(descriptor)
def main()->int:
    try: print(run());return 0
    except (OSError,ValueError,json.JSONDecodeError) as e:print(f"ERROR: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
