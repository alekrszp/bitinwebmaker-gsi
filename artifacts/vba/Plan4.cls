Attribute VB_Name = "Plan4"
Attribute VB_Base = "0{00020820-0000-0000-C000-000000000046}"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True
Attribute VB_TemplateDerived = False
Attribute VB_Customizable = True
'Este modulo possui as funções de data e nome do usuário:
Function DateTime()
DateTime = Now
End Function

Function UserName() As String
    UserName = Application.UserName
End Function

'Function que retorna o nome do usuário de rede logado
 
Function UsuarioRede() As String
    Dim GetUserN
    Dim ObjNetwork
    Set ObjNetwork = CreateObject("WScript.Network")
    GetUserN = ObjNetwork.UserName
    UsuarioRede = GetUserN
    
    Planilha1.Cells(2, 30) = GetUserN ' Preenche o usuário.
    
End Function
