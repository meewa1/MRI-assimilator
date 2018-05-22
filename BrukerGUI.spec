# -*- mode: python -*-

block_cipher = None 

added_files = [('E:\\Users\\Mikhail\\Documents\\Physics\\IGIL\\Work\\Bruker\\BrukerGUI\\pictures\\*.png', 'pictures'),
               ('E:\\Users\\Mikhail\\Documents\\Physics\\IGIL\\Work\\Bruker\\BrukerGUI\\pictures\\*.ico', 'pictures'),
               ('E:\\Users\\Mikhail\\Documents\\Physics\\IGIL\\Work\\Bruker\\BrukerGUI\\*.py', ""),
               ('E:\\Users\\Mikhail\\Documents\\Physics\\IGIL\\Work\\Bruker\\BrukerGUI\\translations\\*.qm', "translations"),
               ('E:\\ProgramData\\Python\\Python36\\Lib\\site-packages\\PyQt5\\Qt\\translations\\qt*_en*.qm', "translations"),
               ('E:\\ProgramData\\Python\\Python36\\Lib\\site-packages\\PyQt5\\Qt\\translations\\qt*_ru*.qm', "translations"),
               ('E:\\ProgramData\\Python\\Python36\\Lib\\site-packages\\scipy\\special\\_ufuncs_cxx.cp36-win_amd64.pyd', '.')
              ]

a = Analysis(['main.py'],
             pathex=['E:\ProgramData\Python\Python36\Lib\site-packages\PyQt5\Qt\bin', 'E:\\Users\\Mikhail\\Documents\\Physics\\IGIL\\Work\\Bruker\\BrukerGUI',
                     'E:\ProgramData\Python\Python36\Lib\site-packages\PyQt5\Qt\translations'],
             binaries=[('E:\\ProgramData\\Python\\Python36\\Lib\\site-packages\\scipy\\extra-dll\\*', '.')],
             datas=added_files,
             hiddenimports=['scipy._lib.messagestream', 'numpy', 'scipy', 
                            'scipy.signal.bsplines', 'scipy._lib', 'scipy._build_utils','scipy.__config__',
                            'scipy.special._ufuncs_cxx',
                            'scipy.linalg.cython_blas',
                            'scipy.linalg.cython_lapack',
                            'scipy.integrate',
                            'scipy.integrate.quadrature',
                            'scipy.integrate.odepack',
                            'scipy.integrate._odepack',
                            'scipy.integrate.quadpack',
                            'scipy.integrate._quadpack',
                            'scipy.integrate._ode',
                            'scipy.integrate.vode',
                            'scipy.integrate._dop',
                            'scipy.integrate.lsoda',
                            'scipy.cluster', 'scipy.constants', 'scipy.misc', 
                            'scipy.odr','scipy.optimize','scipy.setup',
                            'scipy.special','scipy.stats','scipy.version'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='BrukerGUI',
          debug=False,
          strip=False,
          upx=True,
          runtime_tmpdir=None,
          console=True, icon='pictures\\LogoBruker.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='BrukerGUI')
