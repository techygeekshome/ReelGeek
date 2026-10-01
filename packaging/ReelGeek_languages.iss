; ReelGeek installer - languages and custom messages
;
; Kept in its own file so a translation can be added or corrected without touching the
; installer script itself, the same arrangement as DiskGeek and PDFGeek. Adding a language
; means two things: a Name line under [Languages], and a block of messages under
; [CustomMessages] using that same name as the prefix.
;
; The Italian strings follow bovirus's translation for DiskGeek (github.com/bovirus).

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"

[CustomMessages]
english.CreateDesktopShortcut=Create a &desktop shortcut
english.Shortcuts=Additional shortcuts:
english.WebSite={#MyAppName} on the web
english.LaunchApp=Open {#MyAppName}
english.LaunchProgram=Run {#MyAppName}

italian.CreateDesktopShortcut=Crea collegamento programma sul &desktop
italian.Shortcuts=Collegamenti:
italian.WebSite=Sito web {#MyAppName}
italian.CreateQuickLaunchIcon=Crea collegamento programma nella &barra 'Avvio veloce'
italian.NameAndVersion={#MyAppName} {#MyAppVersion}
italian.LaunchProgram=Esegui {#MyAppName}
italian.LaunchApp=Apri {#MyAppName}
italian.AdditionalIcons=Collegamenti:
