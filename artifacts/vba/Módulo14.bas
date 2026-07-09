Attribute VB_Name = "Módulo14"
Sub NEGRITO()
Attribute NEGRITO.VB_ProcData.VB_Invoke_Func = " \n14"
'
' NEGRITO Macro
'

'
    Range("D29").Select
    Selection.Font.Bold = True
    With Selection.Font
        .Color = -16776961
        .TintAndShade = 0
    End With
End Sub


    Range(LINHA01, 4).Select
    Selection.Font.Bold = True
    With Selection.Font
        .Color = -16776961
        .TintAndShade = 0
    End With
End Sub
