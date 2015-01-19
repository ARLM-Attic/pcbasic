# -*- mode: python -*-
basedir = '../..'

a = Analysis([basedir+'/pcbasic'],
             pathex=[basedir],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='pcbasic',
          debug=False,
          strip=None,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries - [
                    ('libcrypto.so.1.0.0', None, None),
                    ('libfreetype.so.6', None, None),
                    ('libncursesw.so.5', None, None),
                    ('libsmpeg-0.4.so.0', None, None),
                    ('libsndfile.so.1', None, None), 
                    ('libvorbisenc.so.2', None, None),
                    ('libvorbis.so.0', None, None),
                    ('libvorbisfile.so.3', None, None),
                    ('libogg.so.0', None, None),
                    ('libpng12.so.0', None, None),
                    ('libmikmod.so.2', None, None),
                    ('libcaca.so.0', None, None),
                    ('libjpeg.so.8', None, None),
                    ('libFLAC.so.8', None, None),
                    ('libblas.so.3gf', None, None),
                    ('liblapack.so.3gf', None, None),
                    ('libgfortran.so.3', None, None),
                    ('libslang.so.2', None, None),
                    ('libtiff.so.4', None, None),
                    ('libquadmath.so.0', None, None),
                    ('libssl.so.1.0.0', None, None),
                    ('libbz2.so.1.0', None, None),
                    ('libdbus-1.so.3', None, None),
                    ('libstdc++.so.6', None, None),
                    ('libreadline.so.6', None, None), 
                    ('libtinfo.so.5', None, None),
                    ('libexpat.so.1', None, None),
                    ('libmad.so.0', None, None),
                    ('libjson.so.0', None, None),
                    ('libgcc_s.so.1', None, None),
                    ('libasyncns.so.0', None, None),
               ]     
               ,
               a.zipfiles,
               a.datas,
               Tree(basedir+'/font', prefix='font'),
               Tree(basedir+'/encoding', prefix='encoding'),
               Tree(basedir+'/info', prefix='info'),
               Tree(basedir+'/config', prefix='config'),
               strip=None,
               upx=True,
               name='pcbasic')
               



