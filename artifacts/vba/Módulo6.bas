Attribute VB_Name = "Módulo6"
Sub limpar3()
Attribute limpar3.VB_ProcData.VB_Invoke_Func = " \n14"
'
' limpar3 Macro
'

'
    Range("B1:B3").Select
    Selection.ClearContents
    Range("A5:CA1000").Select
    Selection.ClearContents
    
    With Selection.Interior
        .Pattern = xlNone
        .TintAndShade = 0
        .PatternTintAndShade = 0
    End With

End Sub
