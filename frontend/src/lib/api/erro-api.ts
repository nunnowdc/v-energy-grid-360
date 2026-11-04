// Erro de uma chamada à API. A mensagem já vem pronta para mostrar na tela.
// status 0 = a resposta nem chegou (servidor fora do ar ou demora demais)
export class ErroApi extends Error {
  status: number

  constructor(status: number, mensagem: string) {
    super(mensagem)
    this.name = 'ErroApi'
    this.status = status
  }
}
