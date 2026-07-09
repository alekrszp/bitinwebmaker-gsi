Attribute VB_Name = "Módulo3"
Sub CLEAR_ZBPP009()
'
' CLEAR_ZBPP009 Macro
'

'
    Rows("2:2").Select
    Range(Selection, Selection.End(xlDown)).Select
    Selection.ClearContents
    Selection.Font.Bold = True
    Selection.Font.Bold = False
    With Selection.Interior
        .Pattern = xlNone
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With
    With Selection.Font
        .ThemeColor = xlThemeColorLight1
        .TintAndShade = 0
    End With
    Selection.RowHeight = 15
    Range("B4").Select
End Sub
