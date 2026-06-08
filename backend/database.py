from models import Quiz, Question, QuestionType, Option

quiz_database: dict[int, Quiz] = {
    1: Quiz(
        id=1,
        title="Pesquisa de Satisfação",
        description="Ajude-nos a melhorar nossos serviços respondendo a esta rápida pesquisa.",
        questions=[
            Question(
                id=1,
                text="Como você avalia nosso atendimento?",
                type=QuestionType.RATING,
                options=[
                    Option(id=1, text="1 - Péssimo"),
                    Option(id=2, text="2 - Ruim"),
                    Option(id=3, text="3 - Regular"),
                    Option(id=4, text="4 - Bom"),
                    Option(id=5, text="5 - Excelente"),
                ],
            ),
            Question(
                id=2,
                text="Quais canais você utilizou? (pode selecionar mais de um)",
                type=QuestionType.MULTIPLE_CHOICE,
                options=[
                    Option(id=1, text="WhatsApp"),
                    Option(id=2, text="E-mail"),
                    Option(id=3, text="Telefone"),
                    Option(id=4, text="Chat online"),
                    Option(id=5, text="Presencial"),
                ],
            ),
            Question(
                id=3,
                text="Você recomendaria nossos serviços para um amigo?",
                type=QuestionType.SINGLE_CHOICE,
                options=[
                    Option(id=1, text="Sim, com certeza"),
                    Option(id=2, text="Talvez"),
                    Option(id=3, text="Não"),
                ],
            ),
            Question(
                id=4,
                text="Deixe seu comentário ou sugestão:",
                type=QuestionType.TEXT,
            ),
        ],
    ),
    2: Quiz(
        id=2,
        title="Quiz de Conhecimentos Gerais",
        description="Teste seus conhecimentos com este quiz rápido!",
        questions=[
            Question(
                id=1,
                text="Qual a capital do Brasil?",
                type=QuestionType.SINGLE_CHOICE,
                options=[
                    Option(id=1, text="Rio de Janeiro"),
                    Option(id=2, text="São Paulo"),
                    Option(id=3, text="Brasília"),
                    Option(id=4, text="Salvador"),
                ],
            ),
            Question(
                id=2,
                text="Quais destes são linguagens de programação? (marque todos)",
                type=QuestionType.MULTIPLE_CHOICE,
                options=[
                    Option(id=1, text="Python"),
                    Option(id=2, text="HTML"),
                    Option(id=3, text="JavaScript"),
                    Option(id=4, text="CSS"),
                    Option(id=5, text="Cobra"),
                ],
            ),
            Question(
                id=3,
                text="Em que ano o homem pisou na Lua pela primeira vez?",
                type=QuestionType.TEXT,
            ),
        ],
    ),
}

submissions: list[dict] = []
submission_counter: int = 0


def get_submission_counter() -> int:
    global submission_counter
    submission_counter += 1
    return submission_counter
