Attribute VB_Name = "Plan2"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
'PINTA AS CÉLULAS CONFORME QUAL TIPO DE ALTERAÇÃO FOR SELECIONADO
Private Sub Worksheet_Change(ByVal Target As Range)
    Dim KeyCells As Range

' The variable KeyCells contains the cells that will
    ' cause an alert when they are changed.
    Set KeyCells = Range("A1:a999999")

If Not Application.Intersect(KeyCells, Range(Target.Address)) _
           Is Nothing Then

' Display a message when one of the designated cells has been
        ' changed.
        ' Place your code here.
        'MsgBox "Linha " & Target.Address & " foi marcada com os campos a serem alterados"
LINHA = Target.Row

'Seleciona células e pinta:
If Plan2.Cells(LINHA, 1) = 1 Then
Rows(LINHA).Interior.Color = vbWhite
Plan2.Cells(LINHA, 2) = "GERAL"
ElseIf Plan2.Cells(LINHA, 1) = Empty Then
Rows(LINHA).Interior.Color = vbWhite
Plan2.Cells(LINHA, 2) = ""

ElseIf Plan2.Cells(LINHA, 1) = 2 Then

'SE FOR (2 - LIBERAÇÃO)2
Range("K" & LINHA).Interior.Color = vbGreen
Range("AC" & LINHA).Interior.Color = vbGreen
Range("AG" & LINHA).Interior.Color = vbGreen
Range("AI" & LINHA).Interior.Color = vbGreen
Plan2.Cells(LINHA, 2) = "LIBERAÇÃO"

'Outras cores:
'Range("A2").Interior.Color = vbBlue
'Range("a4").Interior.Color = vbMagenta
'Range("a5").Interior.Color = vbRed
'Range("a6").Interior.Color = vbGreen
'Range("a7").Interior.Color = vbCyan
'Range("a8").Interior.Color = vbWhite
'Range("a9").Interior.Color = vbBlack

ElseIf Plan2.Cells(LINHA, 1) = 3 Then
'SE FOR (3 - produzido para comprado)
Range("I" & LINHA).Interior.Color = vbGreen
Range("AQ" & LINHA).Interior.Color = vbGreen
Range("AS" & LINHA).Interior.Color = vbGreen
Range("AU" & LINHA).Interior.Color = vbGreen
Range("AY" & LINHA).Interior.Color = vbGreen
Range("BA" & LINHA).Interior.Color = vbGreen
Range("BC" & LINHA).Interior.Color = vbGreen
Range("BE" & LINHA).Interior.Color = vbGreen
Range("BG" & LINHA).Interior.Color = vbGreen
Range("BM" & LINHA).Interior.Color = vbGreen
Plan2.Cells(LINHA, 2) = "PRODUZIDO - COMPRADO"

ElseIf Plan2.Cells(LINHA, 1) = 4 Then
'SE FOR (4 - comprado - produzido)
Range("I" & LINHA).Interior.Color = vbGreen
Range("AQ" & LINHA).Interior.Color = vbGreen
Range("AS" & LINHA).Interior.Color = vbGreen
Range("AU" & LINHA).Interior.Color = vbGreen
Range("AY" & LINHA).Interior.Color = vbGreen
Range("BA" & LINHA).Interior.Color = vbGreen
Range("BC" & LINHA).Interior.Color = vbGreen
Range("BE" & LINHA).Interior.Color = vbGreen
Range("BG" & LINHA).Interior.Color = vbGreen
Range("BM" & LINHA).Interior.Color = vbGreen
Plan2.Cells(LINHA, 2) = "COMPRADO - PRODUZIDO"

ElseIf Plan2.Cells(LINHA, 1) = 5 Then
'SE FOR (5 - Produzido - subcontratado)
Range("I" & LINHA).Interior.Color = vbGreen
Range("AQ" & LINHA).Interior.Color = vbGreen
Range("AS" & LINHA).Interior.Color = vbGreen
Range("AU" & LINHA).Interior.Color = vbGreen
Range("AW" & LINHA).Interior.Color = vbGreen
Range("AY" & LINHA).Interior.Color = vbGreen
Range("BA" & LINHA).Interior.Color = vbGreen
Range("BC" & LINHA).Interior.Color = vbGreen
Range("BE" & LINHA).Interior.Color = vbGreen
Range("BG" & LINHA).Interior.Color = vbGreen
Range("BM" & LINHA).Interior.Color = vbGreen
Plan2.Cells(LINHA, 2) = "PRODUZIDO - SUBCONTRATADO"

ElseIf Plan2.Cells(LINHA, 1) = 6 Then
'SE FOR (6 - subcontratado para produzido)
Range("I" & LINHA).Interior.Color = vbGreen
Range("AQ" & LINHA).Interior.Color = vbGreen
Range("AS" & LINHA).Interior.Color = vbGreen
Range("AU" & LINHA).Interior.Color = vbGreen
Range("AW" & LINHA).Interior.Color = vbGreen
Range("AY" & LINHA).Interior.Color = vbGreen
Range("BA" & LINHA).Interior.Color = vbGreen
Range("BC" & LINHA).Interior.Color = vbGreen
Range("BE" & LINHA).Interior.Color = vbGreen
Range("BG" & LINHA).Interior.Color = vbGreen
Range("BM" & LINHA).Interior.Color = vbGreen
Plan2.Cells(LINHA, 2) = "SUBCONTRATADO - PRODUZIDO"

ElseIf Plan2.Cells(LINHA, 1) = 7 Then
'SE FOR (7 - Eliminar ou desmarcar eliminacao)
Range("BQ" & LINHA).Interior.Color = vbYellow
Range("AE" & LINHA).Interior.Color = vbYellow
Range("AG" & LINHA).Interior.Color = vbYellow
Range("AI" & LINHA).Interior.Color = vbYellow
Range("AL" & LINHA).Interior.Color = vbYellow
Plan2.Cells(LINHA, 2) = "SUBCONTRATADO - PRODUZIDO"
Plan2.Cells(LINHA, 2) = "ELIMINAR OU DESMARCAR ELIMINAÇÃO"


End If
End If

'Descricao = Application.WorksheetFunction.VLookup((Plan2.Cells(linha, 1).Value), Plan5.Range("L1:M7"), 2, 0)

'Plan2.Cells(linha, 2) = Descricao




End Sub


