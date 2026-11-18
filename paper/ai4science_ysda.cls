%% ai4science_ysda.cls
%% Класс статьи для учебной конференции AI4Science-YSDA 2026
%% (курс ШАД «ИИ-ассистенты для исследователя. AI4Science»).
% Основано на стилевом файле П. И. Трошина (версия 3.0, 2025).
%% Версия 1.0, 2026. Кодировка файла UTF-8, сборка pdflatex.
%%
%% Опции класса
%%   без опций   основной язык русский, обезличенная версия
%%   english     основной язык английский
%%   anonymous   обезличенная версия (действует и без указания опции):
%%               авторы, организации, адрес почты и благодарности скрыты,
%%               вместо авторов печатается «Анонимные авторы»
%%   final       итоговая версия: авторы, организации, адрес почты
%%               и благодарности печатаются
%%
%% Команды преамбулы. Действуют для языка, выбранного последней командой
%% \InformationInRussian или \InformationInEnglish (вначале выбран основной
%% язык статьи).
%%   \TITLE{...}             название статьи
%%   \ShortTITLE{...}        короткое название для колонтитула
%%   \AUTHOR{...}            авторы: \aff{1,2} — номера организаций,
%%                           \cormail{адрес} — почта для переписки
%%   \Affil[1]{...}          организация с номером 1
%%   \Abstract{...}          аннотация
%%   \KEYWORDS{...}          ключевые слова
%%   \THANKS{...}            благодарности
%%   \EPIGRAPH[ширина]{...}  эпиграф
%% Блок на втором языке необязателен. Если он задан, печатаются его название,
%% аннотация и ключевые слова (в итоговой версии и благодарности). Авторы
%% печатаются один раз, на основном языке.
%%
%% Пометки авторства (язык пометки задаётся основным языком статьи)
%%   \porozhdeno{...}, \generated{...}   [порождено] / [generated]
%%   \napisano{...},   \written{...}     [написано]  / [written]
%%   \istochnik{...},  \sourced{...}     [источник]  / [source]
%% Необязательный аргумент дописывается в пометку: \porozhdeno[модель]{...}
%% даёт «[порождено: модель]». С пустым обязательным аргументом печатается
%% только пометка.
%% Окружение aiusage — раздел «Использование ИИ-ассистентов» с таблицей
%% «фрагмент — пометка — инструмент или модель — как проверено».

\NeedsTeXFormat{LaTeX2e}[2020/10/01]
\ProvidesClass{ai4science_ysda}[2026/10/18 v1.0 AI4Science-YSDA 2026 paper class]

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% опции %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% основной язык статьи (по умолчанию русский)
\newif\if@mainrussian\@mainrussiantrue
\newif\if@mainenglish\@mainenglishfalse
% язык, к которому относятся команды преамбулы
\newif\if@currentrussian\@currentrussiantrue
\newif\if@currentenglish\@currentenglishfalse
% обезличенная версия (по умолчанию включена)
\newif\if@anonymous\@anonymoustrue

\DeclareOption{english}{\@mainenglishtrue\@mainrussianfalse}
\DeclareOption{russian}{\@mainrussiantrue\@mainenglishfalse}
\DeclareOption{anonymous}{\@anonymoustrue}
\DeclareOption{final}{\@anonymousfalse}
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
% вначале команды преамбулы относятся к основному языку
\if@mainenglish\@currentenglishtrue\@currentrussianfalse\fi

\LoadClass[12pt,a4paper]{article}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% пакеты %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\RequirePackage{cmap}
\RequirePackage[T1,T2A]{fontenc}% T2A — кодировка по умолчанию, T1 — для английского текста
\RequirePackage[utf8]{inputenc}
\if@mainenglish
  \RequirePackage[russian,main=english]{babel}
\else
  \RequirePackage[english,main=russian]{babel}
\fi
\RequirePackage{amsmath}
\RequirePackage{amsthm}
\RequirePackage{amssymb}
\RequirePackage{amsfonts}
\RequirePackage{graphicx}
\RequirePackage{xcolor}
\RequirePackage{floatflt}
\RequirePackage{array}
\RequirePackage{multicol}
\RequirePackage{fancyhdr}
\RequirePackage{tabularx}
\RequirePackage{amsopn}
\RequirePackage{cite}
\RequirePackage{marvosym}% знак \Letter у адреса почты
\if@mainenglish
  \RequirePackage[lang=russian]{bicaption}
\else
  \RequirePackage[lang=english]{bicaption}
\fi
\RequirePackage{subcaption}% подрисунки: окружение subfigure

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% подписи %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% \caption — подпись на основном языке, \bicaption{основной}{второй} — на двух
\captionsetup{singlelinecheck=false, font=small, labelfont=bf, labelsep=period}
% без пробного набора второй подписи до смены языка (нужно, когда
% основной язык английский, а вторая подпись русская)
\captionsetup{bi-slc=false}
\if@mainenglish
  \captionsetup[figure]{name=Fig.}
  \captionsetup[table]{name=Table}
\else
  \captionsetup[figure]{name=Рис.}
  \captionsetup[table]{name=Табл.}
\fi
% метки рисунков в двуязычных подписях выравниваются по ширине
\DeclareCaptionLabelFormat{english-fig}{\makebox[2.75em][l]{Fig.\hfill#2}}
\DeclareCaptionLabelFormat{russian-fig}{\makebox[2.75em][l]{Рис.\hfill#2}}
\DeclareCaptionLabelFormat{english-figbig}{\makebox[3.2em][l]{Fig.\hfill#2}}% номера до 99
\DeclareCaptionLabelFormat{russian-figbig}{\makebox[3.2em][l]{Рис.\hfill#2}}
\newcommand{\setfigureformat}{%
  \ifnum\value{figure}<9
    \if@mainenglish
      \bicaptionsetup[figure]{labelformat=english-fig}{labelformat=russian-fig}%
    \else
      \bicaptionsetup[figure]{labelformat=russian-fig}{labelformat=english-fig}%
    \fi
  \else
    \if@mainenglish
      \bicaptionsetup[figure]{labelformat=english-figbig}{labelformat=russian-figbig}%
    \else
      \bicaptionsetup[figure]{labelformat=russian-figbig}{labelformat=english-figbig}%
    \fi
  \fi}
\if@mainenglish
  \bicaptionsetup[table]{name=Table\hspace*{0.2mm}}{name=\CYRT\cyra\cyrb\cyrl.}
\else
  \bicaptionsetup[table]{name=\CYRT\cyra\cyrb\cyrl.}{name=Table\hspace*{0.2mm}}
\fi
\addto\captionsrussian{\renewcommand{\proofname}{{\hskip\parindent \bf \if@mainenglish Proof\else Доказательство\fi. }}}
\addto\captionsenglish{\renewcommand{\proofname}{\hskip\parindent \bf Proof.}}

% рисунки и таблицы центрируются, размещение по умолчанию !htb
\renewenvironment{figure}[1][\fps@figure]{\setfigureformat
  \edef\@tempa{\noexpand\@float{figure}[#1]}%
  \@tempa\centering}{\end@float}
\def\fps@figure{!htb}
\def\fps@table{!htb}
\renewenvironment{table}[1][\fps@table]{%
  \let\OLDarraystretch\arraystretch
  \renewcommand{\arraystretch}{1.2}% высота строк таблицы
  \hyphenpenalty=10000 % без переносов в таблице
  \edef\@tempa{\noexpand\@float{table}[#1]}%
  \@tempa\centering}{\let\arraystretch\OLDarraystretch\end@float}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% типографика %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\righthyphenmin=2
\emergencystretch=5pt
\hfuzz=2pt
\mathsurround=0.1em
\clubpenalty=10000%
\widowpenalty=10000%
\brokenpenalty=50000%
\frenchspacing%
\tolerance=9000%
\hbadness=1500%
\doublehyphendemerits=50000%
\finalhyphendemerits=25000%
\adjdemerits=50000%
\RequirePackage[a4paper, left=2cm, right=2cm, top=3cm, bottom=3.15cm,
  headheight=15pt]{geometry}
\renewcommand{\baselinestretch}{1.0}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% разделы %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\renewcommand{\theenumi}{\Alph{enumi}}
\renewcommand \thesection {\arabic{section}.}
\renewcommand \thesubsection {\thesection \arabic{subsection}.}
\renewcommand \thesubsubsection {\thesubsection \arabic{subsubsection}.}
\renewcommand{\section}{\@startsection{section}{1}%
  {0pt}{16pt}{4pt}{\bf \centering }}
% подразделы печатаются в строку с текстом, точку в конце заголовка
% ставит автор: \subsection{Название подраздела.}
\renewcommand\subsection{\@startsection{subsection}{2}{\parindent}%
  {\baselineskip}{-0.5em}{\bf }}
\renewcommand\subsubsection{\@startsection{subsubsection}{3}{\parindent}%
  {\baselineskip}{-0.5em}{\bf }}
% номер раздела без точки (для нумерации теорем внутри раздела)
\newcommand\@sectionnumber{\arabic{section}}
% приложения: разделы A., B., ...
\renewcommand\appendix{\par
  \setcounter{section}{0}%
  \setcounter{subsection}{0}%
  \renewcommand\thesection{\Alph{section}.}%
  \renewcommand\@sectionnumber{\Alph{section}}}
\setcounter{tocdepth}{0}
\setcounter{secnumdepth}{5}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% окружения %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Theorem, Theorem_s, Theorem*, Lemma, Proposal, Proposal_s, Corollary,
% Corollary*, Axiom, Example, Definition, Definition_s, Remark, Remark*, Case.
% Окружения с окончанием _s нумеруются внутри раздела: «Теорема 2.1».
\theoremstyle{plain}
\newtheorem{Theorem}{\hskip\parindent \if@mainenglish Theorem\else Теорема\fi}
\newtheorem{Theorem_s}{\hskip\parindent \if@mainenglish Theorem\else Теорема\fi}[section]
\newtheorem*{Theorem*}{\hskip\parindent \if@mainenglish Theorem\else Теорема\fi}
\newtheorem{Lemma}{\hskip\parindent \if@mainenglish Lemma\else Лемма\fi}
\newtheorem{Proposal}{\hskip\parindent \if@mainenglish Proposition\else Предложение\fi}
\newtheorem{Proposal_s}{\hskip\parindent \if@mainenglish Proposition\else Предложение\fi}[section]
\newtheorem{Corollary}{\hskip\parindent \if@mainenglish Corollary\else Следствие\fi}
\newtheorem*{Corollary*}{\hskip\parindent \if@mainenglish Corollary\else Следствие\fi}
\theoremstyle{definition}
\newtheorem{Axiom}{\hskip\parindent \if@mainenglish Axiom\else Аксиома\fi}
\newtheorem{Example}{\hskip\parindent \if@mainenglish Example\else Пример\fi}
\newtheorem{Definition}{\hskip\parindent \if@mainenglish Definition\else Определение\fi}
\newtheorem{Definition_s}{\hskip\parindent \if@mainenglish Definition\else Определение\fi}[section]
\newtheorem*{Remark*}{\hskip\parindent \if@mainenglish Remark\else Замечание\fi}
\newtheorem{Remark}{\hskip\parindent \if@mainenglish Remark\else Замечание\fi}
\theoremstyle{remark}
\newtheorem{Case}{\hskip\parindent \if@mainenglish Case\else Случай\fi}
% номер раздела без завершающей точки: номер теоремы имеет вид «2.1»
\@namedef{theTheorem_s}{\@sectionnumber.\arabic{Theorem_s}}
\@namedef{theProposal_s}{\@sectionnumber.\arabic{Proposal_s}}
\@namedef{theDefinition_s}{\@sectionnumber.\arabic{Definition_s}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% служебное %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% перенос длинной строки без пробелов (адрес, DOI) целиком на новую строку:
% \URL{https://...}
\def\URL{\hfil\penalty 200 \hfilneg \hbox}

% удаление пробелов в начале и в конце аргумента
\long\def\trim@@@spaces#1{%
  \@@trim@@@spaces{\q@mark#1}%
}
\def\@tempa#1{%
  \long\def\@@trim@@@spaces##1{%
    \@@trim@@@spaces@i##1\q@nil\q@mark#1{}\q@mark
      \@@trim@@@spaces@ii
      \@@trim@@@spaces@iii
      #1\q@nil
      \@@trim@@@spaces@iv
      \q@stop
  }%
  \long\def\@@trim@@@spaces@i##1\q@mark#1##2\q@mark##3{%
    ##3%
    \@@trim@@@spaces@i
    \q@mark
    ##2%
    \q@mark#1{##1}%
  }%
  \long\def\@@trim@@@spaces@ii\@@trim@@@spaces@i\q@mark\q@mark##1{%
    \@@trim@@@spaces@iii
    ##1%
  }%
  \long\def\@@trim@@@spaces@iii##1#1\q@nil##2{%
    ##2%
    ##1\q@nil
    \@@trim@@@spaces@iii
  }%
  \long\def\@@trim@@@spaces@iv##1\q@nil##2\q@stop{%
    \@gobble##1%
  }%
}
\@tempa{ }

% выбор языка для команд преамбулы
\newcommand{\InformationInRussian}{\@currentrussiantrue\@currentenglishfalse}
\newcommand{\InformationInEnglish}{\@currentrussianfalse\@currentenglishtrue}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% сведения о статье %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% название
\def\@ArticleNAME{}\def\@ArticleNAMEeng{}
\newcommand{\TITLE}[1]{%
  \if@currentrussian\def\@ArticleNAME{#1}\else\def\@ArticleNAMEeng{#1}\fi}

% короткое название для колонтитула
\def\@ArticleHEAD{}\def\@ArticleHEADeng{}
\newcommand{\ShortTITLE}[1]{%
  \if@currentrussian\def\@ArticleHEAD{#1}\else\def\@ArticleHEADeng{#1}\fi}

% эпиграф
\def\@epigraph{}\def\@epigrapheng{}
\newlength\@epigraphwidth
\newlength\@epigraphengwidth
\newcommand{\EPIGRAPH}[2][0.5\textwidth]{%
  \if@currentrussian
    \def\@epigraph{#2}\setlength\@epigraphwidth{#1}%
  \else
    \def\@epigrapheng{#2}\setlength\@epigraphengwidth{#1}%
  \fi}

% авторы: \aff{номера организаций}, \cormail{адрес почты для переписки}
\newcommand{\aff}[1]{\unskip$^{#1}$\!}
\def\@ArticleAUTHOR{}\def\@ArticleAUTHOReng{}
\def\@ArticleAUTHORHEAD{}\def\@ArticleAUTHORHEADeng{}% без номеров и почты
\def\@NumOfAuthors{0}% 1 — один автор, 0 — несколько
% 1, если в списке нет запятой (один автор), иначе 0
\def\@checkforcomma#1,#2\@nil{\if\relax#2\relax 1\else 0\fi}
\newcommand{\IfContainsComma}[1]{\expandafter\@checkforcomma#1,\@nil}
\newcommand{\AUTHOR}[1]{%
  \begingroup
    \def\aff##1{}\def\cormail##1{}%
    \protected@xdef\@tempauthorhead{#1}%
  \endgroup
  \if@currentrussian
    \def\@ArticleAUTHOR{#1}\let\@ArticleAUTHORHEAD\@tempauthorhead
    \if@mainrussian\edef\@NumOfAuthors{\IfContainsComma{\@tempauthorhead}}\fi
  \else
    \def\@ArticleAUTHOReng{#1}\let\@ArticleAUTHORHEADeng\@tempauthorhead
    \if@mainenglish\edef\@NumOfAuthors{\IfContainsComma{\@tempauthorhead}}\fi
  \fi}
\def\cormail@{}
\newcommand{\cormail}[1]{\gdef\cormail@{#1}%
  \ifnum\@NumOfAuthors=1 \else\unskip$^{\mbox{\,\Letter}}$\!\fi}

% первый автор и «и др.» / «et al.», если авторов больше двух
\ExplSyntaxOn
\NewDocumentCommand{\ExtractFirst}{m}
  {
    \seq_set_split:Nnn \l_tmpa_seq { , } { #1 }
    \int_compare:nTF { \seq_count:N \l_tmpa_seq > 2 }
      { \seq_item:Nn \l_tmpa_seq { 1 } ~и~др. }
      { #1 }
  }
\NewDocumentCommand{\ExtractFirstEng}{m}
  {
    \seq_set_split:Nnn \l_tmpa_seq { , } { #1 }
    \int_compare:nTF { \seq_count:N \l_tmpa_seq > 2 }
      { \seq_item:Nn \l_tmpa_seq { 1 } ~et~al. }
      { #1 }
  }
\ExplSyntaxOff

% организации: \Affil[номер]{название, город, страна}
\def\Affilblock@{}\def\Affilblockeng@{}
\newcommand{\Affil}[2][]{%
  \edef\@temp@{\trim@@@spaces{#2}}%
  \ifx\@temp@\@empty
  \else
    \if@currentrussian
      \g@addto@macro\Affilblock@{%
        \vspace*{-0.12cm}%
        {\centering\it\footnotesize
          \ifx#1\@empty\else$^{#1}$\!\fi#2
          \vspace*{0.3cm}% пустая строка ниже нужна для \centering

        }}%
    \else
      \g@addto@macro\Affilblockeng@{%
        \vspace*{-0.12cm}%
        {\centering\it\footnotesize
          \ifx#1\@empty\else$^{#1}$\!\fi#2
          \vspace*{0.3cm}% пустая строка ниже нужна для \centering

        }}%
    \fi
  \fi}

% аннотация, ключевые слова, благодарности
\def\@Abstract{}\def\@Abstracteng{}
\newcommand{\Abstract}[1]{%
  \if@currentrussian\def\@Abstract{#1}\else\def\@Abstracteng{#1}\fi}
\def\@Keywords{}\def\@Keywordseng{}
\newcommand{\KEYWORDS}[1]{%
  \if@currentrussian\def\@Keywords{#1}\else\def\@Keywordseng{#1}\fi}
\def\@Thanks{}\def\@Thankseng{}
\newcommand{\THANKS}[1]{%
  \if@currentrussian
    \def\@Thanks{\vspace{\baselineskip}\textbf{Благодарности.} #1}%
  \else
    \def\@Thankseng{\vspace{\baselineskip}\textbf{Acknowledgments.} #1}%
  \fi}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% конференция %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\newcommand\@venuename{AI4Science-YSDA 2026}
\newcommand\@venueline{%
  \if@mainenglish
    Submitted to \@venuename, the student conference of the YSDA course
    “AI Assistants for Researchers”%
  \else
    Статья подана на учебную конференцию \@venuename\ (курс ШАД
    «ИИ-ассистенты для исследователя»)%
  \fi}
\newcommand\@anonauthors{%
  \if@currentenglish Anonymous authors\else Анонимные авторы\fi}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% колонтитулы %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% вверху: авторы | короткое название, номер страницы
% внизу: название конференции
\newcommand\@headauthors{%
  \if@anonymous
    \if@mainenglish Anonymous authors\else Анонимные авторы\fi
  \else
    \if@mainenglish
      \expandafter\ExtractFirstEng\expandafter{\@ArticleAUTHORHEADeng}%
    \else
      \expandafter\ExtractFirst\expandafter{\@ArticleAUTHORHEAD}%
    \fi
  \fi}
\newcommand\@headtext{%
  \if@mainenglish\let\@headtitle\@ArticleHEADeng\else\let\@headtitle\@ArticleHEAD\fi
  \rm\textcolor[gray]{0.3}{\@headauthors}%
  \ifx\@headtitle\@empty\else\ |\ \@headtitle\fi}
\newcommand\@venuefooter{%
  \begin{tabular}[b]{@{}c@{}}
    \hline
    \rule{0pt}{2.6ex}\small\@venuename
  \end{tabular}}
\newcommand{\setheader}{%
  \pagestyle{fancy}%
  \renewcommand{\headrulewidth}{0.4pt}%
  \renewcommand{\footrulewidth}{0pt}%
  \fancyhf{}%
  \if@twoside
    \fancyhead[CO]{\hfill\@headtext\hfill\thepage}%
    \fancyhead[CE]{\thepage\hfill\@headtext\hfill}%
    \fancyfoot[RO,LE]{\@venuefooter}%
  \else
    \fancyhead[C]{\hfill\@headtext\hfill\thepage}%
    \fancyfoot[R]{\@venuefooter}%
  \fi}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% заголовок статьи %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\renewenvironment{abstract}{%
  \small
  \vspace*{-0.5cm}%
  \begin{center}{\bfseries\abstractname\nopagebreak\vspace{-0.4em}}\end{center}%
  \nopagebreak
  \par}{\par}

\newcommand\@printepigraph{%
  \if@currentenglish\let\@curepigraph\@epigrapheng\setlength\@tempdima\@epigraphengwidth
  \else\let\@curepigraph\@epigraph\setlength\@tempdima\@epigraphwidth\fi
  \ifx\@curepigraph\@empty\else
    \hfill\begin{minipage}{\@tempdima}\raggedright\small\@curepigraph\end{minipage}%
  \fi}

% авторы, организации и почта (только в итоговой версии)
\newcommand\@printauthors{%
  \if@anonymous
    \begin{center}\large\bfseries\@anonauthors\end{center}%
  \else
    \begin{center}\large\bfseries
      \if@currentenglish\@ArticleAUTHOReng\else\@ArticleAUTHOR\fi
    \end{center}%
    \if@currentenglish\Affilblockeng@\else\Affilblock@\fi
    \ifx\cormail@\@empty\else
      \vspace*{-0.4cm}%
      \begin{center}\small\itshape
        \ifnum\@NumOfAuthors=1 \else${}^{\mbox{\Letter}}$\,\fi
        \cormail@
      \end{center}%
    \fi
  \fi}

% Блок сведений на текущем языке (\@currentrussiantrue или \@currentenglishtrue).
% #1 = 1 — основной блок, 0 — блок на втором языке
\newcommand\@frontblock[1]{%
  \if@currentenglish
    \selectlanguage{english}%
    \let\@curtitle\@ArticleNAMEeng\let\@curabstract\@Abstracteng
    \let\@curkeywords\@Keywordseng\let\@curthanks\@Thankseng
  \else
    \selectlanguage{russian}%
    \let\@curtitle\@ArticleNAME\let\@curabstract\@Abstract
    \let\@curkeywords\@Keywords\let\@curthanks\@Thanks
  \fi
  \vbox{%
    \ifnum#1=1
      \begin{flushleft}\small\@venueline\end{flushleft}%
    \fi
    \@printepigraph
    \begin{center}%
      \ifnum#1=1 \vspace*{0.3cm}\Large\else\large\fi
      \bfseries\@curtitle
    \end{center}%
    \ifnum#1=1 \@printauthors\fi
  }%
  \renewcommand{\abstractname}{\if@currentenglish Abstract\else Аннотация\fi}%
  \ifx\@curabstract\@empty\else
    \begin{abstract}\@curabstract\end{abstract}%
  \fi
  \ifx\@curkeywords\@empty\else
    \vspace{\baselineskip}%
    {\small\textbf{\if@currentenglish Keywords:\else Ключевые слова:\fi} \@curkeywords\par}%
  \fi
  \if@anonymous\else{\small\@curthanks\par}\fi
  \par}

\newcommand\@printfrontmatter{%
  \if@mainenglish
    \@currentenglishtrue\@currentrussianfalse\@frontblock{1}%
    \ifx\@ArticleNAME\@empty\else
      \vspace{0.5\baselineskip}%
      \@currentrussiantrue\@currentenglishfalse\@frontblock{0}%
    \fi
    \selectlanguage{english}%
  \else
    \@currentrussiantrue\@currentenglishfalse\@frontblock{1}%
    \ifx\@ArticleNAMEeng\@empty\else
      \vspace{0.5\baselineskip}%
      \@currentenglishtrue\@currentrussianfalse\@frontblock{0}%
    \fi
    \selectlanguage{russian}%
  \fi
  \par\vspace{6pt}%
  \hrule
  \vspace{8pt}}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% пометки авторства %%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% #1: 0 — порождено, 1 — написано, 2 — источник
\newcommand\@aitagname[1]{%
  \if@mainenglish
    \ifcase#1 generated\or written\or source\fi
  \else
    \ifcase#1 порождено\or написано\or источник\fi
  \fi}
% #1 — вид пометки, #2 — примечание (может быть пустым)
% (вид пометки не переносится, примечание переносится по пробелам)
\newcommand\@aitag[2]{%
  \textcolor[gray]{0.4}{\footnotesize\upshape\mdseries
    \if\relax\detokenize{#2}\relax
      \mbox{[\@aitagname{#1}]}%
    \else
      \mbox{[\@aitagname{#1}:}~#2]%
    \fi}}
% #1 — вид пометки, #2 — примечание, #3 — помеченный фрагмент
\long\def\@aimark#1#2#3{%
  \if\relax\detokenize{#3}\relax
    \@aitag{#1}{#2}%
  \else
    #3\unskip\nobreak\hspace{0.3em}\@aitag{#1}{#2}%
  \fi}
\NewDocumentCommand\porozhdeno{O{}+m}{\@aimark{0}{#1}{#2}}
\NewDocumentCommand\napisano{O{}+m}{\@aimark{1}{#1}{#2}}
\NewDocumentCommand\istochnik{O{}+m}{\@aimark{2}{#1}{#2}}
\NewDocumentCommand\generated{O{}+m}{\@aimark{0}{#1}{#2}}
\NewDocumentCommand\written{O{}+m}{\@aimark{1}{#1}{#2}}
\NewDocumentCommand\sourced{O{}+m}{\@aimark{2}{#1}{#2}}

% Раздел «Использование ИИ-ассистентов»: заголовок и таблица.
% Каждая строка: фрагмент & пометка & инструмент или модель & как проверено \\
% Необязательный аргумент — текст перед таблицей.
\newcommand\@aiusagehead{%
  \if@mainenglish
    \gdef\@aiusagerow{\textbf{Fragment or section} & \textbf{Tag} &
      \textbf{Tool or model} & \textbf{How it was checked}}%
  \else
    \gdef\@aiusagerow{\textbf{Фрагмент или раздел} & \textbf{Пометка} &
      \textbf{Инструмент или модель} & \textbf{Как проверено}}%
  \fi}
\newenvironment{aiusage}[1][]{%
  \section*{\if@mainenglish Use of AI assistants\else Использование ИИ-ассистентов\fi}%
  \if\relax\detokenize{#1}\relax\else #1\par\fi
  \@aiusagehead
  \par\noindent
  \small
  \renewcommand{\arraystretch}{1.15}%
  % ширины столбцов: 0,22 + 0,14 + 0,24 + 0,40 ширины текста
  \begin{tabular}{@{}%
      >{\raggedright\arraybackslash}p{\dimexpr0.22\textwidth-1.5\tabcolsep\relax}%
      >{\raggedright\arraybackslash}p{\dimexpr0.14\textwidth-1.5\tabcolsep\relax}%
      >{\raggedright\arraybackslash}p{\dimexpr0.24\textwidth-1.5\tabcolsep\relax}%
      >{\raggedright\arraybackslash}p{\dimexpr0.40\textwidth-1.5\tabcolsep\relax}@{}}
    \hline
    \@aiusagerow\\
    \hline
}{%
    \hline
  \end{tabular}\par}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% литература %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% один список литературы на основном языке статьи
\renewcommand{\@biblabel}[1]{#1. \hfill}
\let\OLDthebibliography\thebibliography
\renewcommand\thebibliography[1]{%
  \if@mainenglish
    \renewcommand{\refname}{\normalsize References}%
  \else
    \renewcommand{\refname}{\normalsize Литература}%
  \fi
  \baselineskip=12pt
  \small
  \OLDthebibliography{#1}}

\hyphenation{Наука} % слова без переносов
\hyphenation{науки}

\newcommand{\mypagebreak}{\linebreak

\pagebreak

\noindent }

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% метаданные PDF %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\RequirePackage[unicode,hidelinks]{hyperref}
\urlstyle{same}% адреса \url{...} набираются шрифтом основного текста
\pdfstringdefDisableCommands{\def\\{ }\def\aff#1{}\def\cormail#1{}}
% в обезличенной версии поле автора пустое, а в PDF не записываются
% служебные сведения pdfTeX о вставленных файлах (имена и пути файлов
% рисунков и их собственные метаданные)
\if@anonymous
  \ifdefined\pdfsuppressptexinfo\pdfsuppressptexinfo=-1\relax\fi
\fi
\newcommand\@setpdfinfo{%
  \if@mainenglish
    \hypersetup{pdftitle={\@ArticleNAMEeng}, pdfkeywords={\@Keywordseng}}%
  \else
    \hypersetup{pdftitle={\@ArticleNAME}, pdfkeywords={\@Keywords}}%
  \fi
  \hypersetup{pdfsubject={\@venuename}}%
  \if@anonymous
    \hypersetup{pdfauthor={}}%
  \else
    \if@mainenglish
      \hypersetup{pdfauthor={\@ArticleAUTHORHEADeng}}%
    \else
      \hypersetup{pdfauthor={\@ArticleAUTHORHEAD}}%
    \fi
  \fi}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% начало документа %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Заголовок статьи печатается автоматически, \maketitle не нужен.
\AddToHook{begindocument}{\setheader\@setpdfinfo}
\AddToHook{begindocument/end}{\@printfrontmatter}

\endinput
