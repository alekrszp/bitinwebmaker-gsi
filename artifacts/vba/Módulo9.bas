Attribute VB_Name = "Módulo9"
Sub linhadivid()
Attribute linhadivid.VB_ProcData.VB_Invoke_Func = " \n14"
'
' linhadivid Macro
'

'
    Rows("12:12").Select
    With Selection.Interior
        .PatternColorIndex = xlAutomatic
        .ThemeColor = xlThemeColorLight1
        .TintAndShade = 4.99893185216834E-02
        .PatternTintAndShade = 0
    End With
    Selection.RowHeight = 6.75
    Rows("12:12").Select
    Selection.Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove
    Range("B15").Select
End Sub
