Attribute VB_Name = "Módulo8"
Sub pintatudo()
Attribute pintatudo.VB_ProcData.VB_Invoke_Func = " \n14"
'
' pintatudo Macro
'

'
    Rows("5:5").Select
    With Selection.Interior
        .PatternColorIndex = xlAutomatic
        .ThemeColor = xlThemeColorDark1
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With
    Range("B14").Select
End Sub
