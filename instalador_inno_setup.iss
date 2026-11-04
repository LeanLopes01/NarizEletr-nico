; Script Inno Setup preparado para o Nariz Eletronico (Arduino UNO R3 — v0.4.3)
; Baseado no padrao de instalacao de C:\ProjetoTablepRPG\Outros\DiceVTT-setup-real.iss
;
; COMO USAR QUANDO ESTIVER PRONTO PARA LANCAR A PRIMEIRA VERSAO:
; 1. Gere o executavel rodando "gerar_exe_pyinstaller.bat" (cria dist\NarizEletronico\NarizEletronico.exe)
; 2. Compile este arquivo no Inno Setup (ISCC.exe) ou execute "python automacao_release\novaVersao.py"

#define MyAppName "NarizEletronico"
#define MyAppDisplayName "E-Nose Control & Analytics (Nariz Eletronico)"
#define MyAppVersion "0.4.3"
#define MyAppPublisher "USP / Iniciacao Cientifica — LeanLopes01"
#define MyAppURL "https://github.com/LeanLopes01/NarizEletr-nico"
#define MyAppExeName "NarizEletronico.exe"

[Setup]
AppId={{8A4E62D1-7C19-4E53-9B8A-3F7E12C40430}
AppName={#MyAppDisplayName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=nariz-eletronico-{#MyAppVersion}-setup
SolidCompression=yes
WizardStyle=modern dynamic windows11

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\NarizEletronico\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\NarizEletronico\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "version.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "nariz_eletronico.ino"; DestDir: "{app}\arduino\nariz_eletronico"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppDisplayName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppDisplayName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
