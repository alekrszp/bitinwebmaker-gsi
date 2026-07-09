Attribute VB_Name = "Módulo5"
Sub INSERIR_LINHA()
Attribute INSERIR_LINHA.VB_ProcData.VB_Invoke_Func = " \n14"
'
' INSERIR_LINHA Macro
'

'
    Rows("109:109").Select
    Selection.Insert Shift:=xlDown, CopyOrigin:=xlFormatFromLeftOrAbove
    Range("C110").Select
End Sub
