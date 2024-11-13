import itertools as it
import os
import subprocess
from pathlib import Path

import rich
import pytest
from fastapi.testclient import TestClient

import ipd
import ppp

def main():
    def funcsetup(client, backend):
        ppp.server.add_defaults(client)

    ipd.tests.maincrudtest(ppp.tests.ppp_test_stuff, globals(), funcsetup=funcsetup)

def set_debug_requests():
    import http.client as http_client
    import logging

    http_client.HTTPConnection.debuglevel = 1
    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def _test_post_hang():
    # only hangs if pollfileid is a string... any string
    import requests
    url = 'http://localhost:12346/ppp/create/review'
    # body = '''{"id":"40d493e7-fb18-44b5-be1c-a5154ad0c4d8","ispublic":true,"telemetry":false,"ghost":false,"datecreated":"2024-10-13T23:16:57.436648","props":[],"attrs":{},"userid":"24c41db4-7e45-4265-b666-71f477955a01","pollid":"7cf6d8f5-f9d1-4563-99f7-1a95d429dd68","grade":"dislike","comment":"","pollfileid":"2bbfa731-949f-4dfe-8119-94fdae221b8e"}'''
    body = '''{"pollfileid":""}'''
    # ic(url, body)
    response = requests.post(url, body)
    assert response.content.count(b'bad UUID string')

@pytest.mark.fast
def test_pollfiles(client):
    poll = client.newpoll(name='polio', path=ipd.dev.package_testdata_path('ppppdbdir'))
    for f in poll.pollfiles:
        assert f == client.pollfile(pollid=poll.id, fname=f.fname)

@pytest.mark.fast
def test_review(client):
    poll = client.newpoll(name='polio', path=ipd.dev.package_testdata_path('ppppdbdir'))
    assert poll.pollfiles
    poll2 = client.newpoll(name='polio2', path=ipd.dev.package_testdata_path('ppppdbdir'))
    poll3 = client.newpoll(name='polio3', path=ipd.dev.package_testdata_path('ppppdbdir'))
    file = next(iter(poll.pollfiles))
    client.newuser(name='reviewer')
    ic([p.name for p in client.users()])
    # ic(client.user(name='reviewer'))
    rev = client.newreview(userid='reviewer', pollid=poll.id, pollfileid=file.id, workflowid='Manual', grade='dislike')
    assert client.reviews()[0].user.name == 'reviewer'
    assert os.path.exists(rev.pollfile.permafname)
    # ic('\n'.join([f'{f.pollid} {f.fname}' for f in client.pollfiles()]))
    polls = client.polls()
    review = ppp.ReviewSpec(pollid=polls[2].id, pollfileid=polls[2].pollfiles[2].id, grade='superlike', comment='foobar')
    assert review.grade == 'superlike'
    result = client.upload_review(review)
    assert isinstance(result, ppp.Review)
    # rich.ic(client.reviews())
    assert len(client.reviews()) == 2
    result = client.upload(ppp.ReviewSpec(pollid=poll2.id, pollfileid=poll2.pollfiles[2].id, grade='hate'))
    assert isinstance(result, ppp.Review)
    assert file.fname in [f.fname for f in poll.pollfiles]
    assert client.poll(id=poll.id)
    assert client.pollfile(pollid=poll.id, fname=poll.pollfiles[0].fname)
    ic(len(client.pollfile(pollid=poll.id, fname=file.fname).reviews))
    assert 1 == len(client.pollfile(pollid=poll.id, fname=file.fname).reviews)
    assert 3 == len(client.reviews())
    assert 1 == len(list(it.chain(*(f.reviews for f in client.pollfiles(fname=file.fname)))))
    reviews = client.reviews()
    polls = client.polls()
    files = client.pollfiles()

    for i, p in enumerate(client.polls()):
        ic(i, len(p.reviews))
    assert isinstance(files[0], ppp.PollFile)
    assert isinstance(polls[2].pollfiles[0], ppp.PollFile)
    assert isinstance(reviews[2].pollfile, ppp.PollFile)
    assert isinstance(reviews[0], ppp.Review)
    assert isinstance(polls[1].reviews[0], ppp.Review)
    assert isinstance(files[1].poll, ppp.Poll)

    for r in reviews:
        # ic('permafname', r.pollfile.permafname)
        # ic(r.pollfile)
        assert os.path.exists(r.pollfile.permafname)

    # ic([p.name for p in client.polls()])
    # ic(len(client.polls(name='foo1')))

@pytest.mark.fast
def test_poll_attr(client):
    poll = client.upload_poll(ppp.PollSpec(name='foo', path=ipd.dev.package_testdata_path('ppppdbdir')))
    # poll.print_full()
    # ic(type(poll.id), type(poll.pollfiles[0].pollid))
    # ic(poll.id == poll.pollfiles[0].pollid)
    assert all(poll.id == p.pollid for p in poll.pollfiles)
    assert isinstance(poll.pollfiles[0], ppp.PollFile)

# def test_spec_srict_ctor_override():
#     class Foo(pydantic.BaseModel, ipd.crud.StrictFields):
#         bar: int
#
#     a = Foo(bar=6)
#     with pytest.raises(TypeError):
#         b = Foo(baz=6)
#
#     class FooNonstrict(Foo):
#         bar: int
#
#         def __init__(self, zaz, **kw):
#             super().__init__(**kw)
#
#     c = FooNonstrict(zaz=6, bar=6)

@pytest.mark.fast
def test_setattr(client):
    user = client.newuser(name='foo', fullname='bar')
    assert user.fullname == 'bar'
    user.fullname = 'baz'
    usercopy = client.user(id=user.id)
    assert usercopy.fullname == 'baz'
    assert user.fullname == 'baz'

@pytest.mark.fast
def test_pollinfo(client, backend):
    backend.newpoll(name='foo', path='.', ispublic=True, user=backend.newuser(name='foo'))
    backend.newpoll(name='bar', path='.', ispublic=False, user=backend.newuser(name='bar'))
    backend.newpoll(name='baz', path='.', ispublic=True, user=backend.newuser(name='baz'))
    assert len(backend.polls()) == 3
    assert len(backend.pollinfo(user='foo')) == 2
    assert len(backend.pollinfo(user='bar')) == 3
    assert len(backend.pollinfo(user='baz')) == 2
    binfo = backend.pollinfo(user='admin')
    info = client.pollinfo(user='admin')
    assert binfo == info

@pytest.mark.fast
def test_pymolcmdsdict(client):
    pcd = client.pymolcmdsdict()
    # ic(client.pymolcmds())
    # ic(pcd)
    assert isinstance(pcd, list)
    assert isinstance(pcd[0], dict)
    cmds = client.pymolcmds()
    cmd = cmds[0]

@pytest.mark.fast
def test_ghost(backend):
    user = backend.newuser(name='jameswoods')
    poll = backend.newpoll(name='foo', path='bar', user=user)
    ic(backend.newpollfile)
    file = backend.newpollfile(fname='baz', pollid=poll.id)
    poll.pollfiles.append(file)
    backend.session.commit()
    assert not file.ghost
    ic(poll.clear)
    poll.clear(backend)
    assert file.ghost
    assert 1 == len(backend.pollinfo(user=user.name))
    assert not poll.ghost
    backend.remove('poll', poll.id)
    assert poll.ghost
    assert 0 == len(backend.pollinfo(user=user.name))

@pytest.mark.fast
def test_user_backend(backend):
    foo = backend.newuser(name='foo')
    assert backend.iserror(backend.newuser(name='foo'))
    ic('!' * 80)
    return

    follower = backend.newuser(name='following1')
    follower.following.append(foo)
    follower.following.append(foo)
    follower.following.append(foo)
    backend.session.commit()
    assert follower in foo.followers
    assert len(foo.followers) == 1
    assert len(follower.following) == 1
    foo.followers = []
    assert follower not in foo.followers
    assert foo not in follower.following

# def test_spec_basics():
#     with pytest.raises(TypeError):
#         ppp.PollSpec(name='foo', path='.', userid='test', ntisearien=1)

@pytest.mark.fast
def test_access_all(client, backend):
    assert 0 == (len(client.polls()))

def _test_file_upload(client, backend):
    # client = ppp.PPPClient(ppptestclient)
    path = ipd.dev.package_testdata_path('ppppdbdir')
    spec = ppp.PollSpec(name='usertest1pub', path=path, userid='test', ispublic=True)
    if response := client.upload_poll(spec): ic(response)
    localfname = os.path.join(path, '1pgx.cif')
    file = ppp.PollFileSpec(pollid=spec.id, fname=localfname)
    poll = client.upload(ppp.PollSpec(name='foo', path='.'))
    assert isinstance(poll, ppp.Poll), poll
    exists, newfname = client.get('/have/pollfile', fname=file.fname, pollid=client.polls()[-1].id)
    assert file.fname in [f.fname for f in client.pollfiles()]
    assert newfname.endswith('\\ipd\\tests\\data\\ppppdbdir\\1pgx.cif')
    exists, newfname = backend.have_pollfile(fname=localfname, pollid=client.polls()[-1].id)
    # ic(exists, f'"{newfname}"')
    assert newfname.endswith('\\ipd\\tests\\data\\ppppdbdir\\1pgx.cif')
    filecontent = Path(localfname).read_text()
    file.filecontent = filecontent
    file.permafname = newfname
    file = ppp.PollFileSpec(**file.dict())
    # response = backend.create_file(file)
    client.post('/create/pollfilecontents', file)
    ic(newfname)
    diff = subprocess.check_output(['diff', localfname, newfname])
    if diff: ic(f'diff {localfname} {newfname} {diff}')
    assert not diff
    os.remove(newfname)
    file.filecontent = ''
    files = [file._copy_with_newid() for _ in range(10)]
    backend.create_empty_files(files)
    poll = client.polls(name='usertest1pub')[0]
    ic(client.npollfiles())
    # for p in client.pollfiles():
    # ic(f'{p.poll.name} {p.fname}')
    assert client.npollfiles() == 15
    assert len(client.pollfiles()) == 15
    client.remove(poll)
    assert len(client.polls()) == 1

@pytest.mark.fast
def test_poll(client, backend):
    path = ipd.dev.package_testdata_path('ppppdbdir')
    client.upload(ppp.UserSpec(name='test1'))

    assert client.user(name='test1').fullname == ''
    client.user(name='test1').fullname = 'fulllname'
    assert client.user(name='test1').fullname == 'fulllname'

    client.upload(ppp.UserSpec(name='test2'))
    client.upload(ppp.UserSpec(name='test3'))
    client.upload_poll(ppp.PollSpec(name='usertest1pub', path=path, userid='test1', ispublic=True))
    client.upload_poll(ppp.PollSpec(name='usertest1pri', path=path, userid='test1', ispublic=False))
    client.upload_poll(ppp.PollSpec(name='usertest2pub', path=path, userid='test2', ispublic=True))
    client.upload_poll(ppp.PollSpec(name='usertest3pri', path=path, userid='test3', ispublic=False))
    assert 3 == len(client.pollinfo(user='test1'))
    assert 2 == len(client.pollinfo(user='test2'))
    assert 3 == len(client.pollinfo(user='test3'))
    assert 2 == len(client.pollinfo(user='sheffler'))
    assert 5 == len(client.pollinfo(user='admin'))

    poll = client.upload_poll(ppp.PollSpec(name='foo1', desc='bar', path=path))
    assert isinstance(poll, ppp.Poll)
    poll = client.upload_poll(ppp.PollSpec(name='foo2', desc='Nntsebar', path=path))
    assert isinstance(poll, ppp.Poll)
    poll = client.upload_poll(ppp.PollSpec(name='foo3', desc='barntes', path=path))

    assert len(client.polls()) == 7
    polljs = client.get('/polls')
    # ic(polljs)
    # polls = [ppp.Poll(**_) for _ in polljs]
    polls = backend.polls()
    # for poll in polls:
    # ic(poll, len(poll.files))
    # ic(list(poll.files)[:2])

    pfiles = polls[1].pollfiles
    assert len(pfiles) == 3

    poll3 = client.polls()[6]
    # ic(poll3)

    poll = ppp.PollSpec(name='foobar', path=path)
    # ic(poll)
    poll = client.upload_poll(poll)
    assert len(client.polls()) == 8
    poll = client.polls()[6]
    assert isinstance(poll, ppp.Poll)
    # for p in client.polls():
    # ic(p.id, p.name, len(p.files))
    assert len(poll.pollfiles) == 3
    assert isinstance(poll.pollfiles[0], ppp.PollFile)

    result = client.upload(ppp.PymolCMDSpec(name='test', cmdon='show lines', cmdoff='hide lines', userid='test'))
    assert isinstance(result, ppp.PymolCMD)
    result = client.upload(ppp.PymolCMDSpec(name='test2', cmdon='fubar', cmdoff='hide lines', userid='test'))

    # ic(result)
    with pytest.raises(ipd.crud.ClientError):
        result = client.upload(ppp.PymolCMDSpec(name='test', cmdon='show lines', cmdoff='hide lines', userid='test'))
    # ic(result)
    ic('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    assert len(client.pymolcmds(user='test')) == 1

if __name__ == '__main__':
    main()
