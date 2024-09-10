FROM python:3.10

ENV TZ=Etc/UTC
ENV DOCKER_HOST=unix:///var/run/user/1000/docker.sock

ARG USERNAME=devcontainer
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Install git, process tools, lsb-release (common in install instructions for CLIs) and curl
# RUN apk --no-cache update && apk --no-cache upgrade && \
# 	apk add --no-cache gcc musl-dev linux-headers libffi-dev bash zsh git curl sudo build-base openssh-client pkgconfig docker-cli gtk+3.0

RUN apt-get update && apt-get install -y \
	apt-utils \
	locales \
	locales-all \
	ca-certificates \
	curl \
	git \
	openssh-client \
	procps \
	sudo \
	zsh \
	gnupg \
	lsb-release \
	&& apt-get clean

RUN pip install --no-cache-dir --upgrade pip && \
	pip install --no-cache-dir wheel pre-commit

RUN install -m 0755 -d /etc/apt/keyrings && \
	curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
	chmod a+r /etc/apt/keyrings/docker.asc && \
	echo \
	"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
	$(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
	(sudo tee /etc/apt/sources.list.d/docker.list > /dev/null) && \
	apt-get update && apt-get install -y docker-ce-cli docker-buildx-plugin docker-compose-plugin

# change default shell from bash to zsh
RUN sed -i -e "s/bin\/ash/bin\/zsh/" /etc/passwd

# Create the user
RUN addgroup --gid $USER_GID $USERNAME \
	&& adduser --gecos GECOS --disabled-password --uid $USER_UID --gid $USER_GID --shell /bin/zsh $USERNAME
# add user to sudoer
RUN echo "$USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# change user
USER $USERNAME

# install oh-my-zsh
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
# install zsh plugins auto suggestions and syntax highlighting
RUN git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

COPY config/zshrc /home/$USERNAME/.zshrc

COPY config/gitconfig /home/$USERNAME/.gitconfig

VOLUME [ "/workspaces/CrossMgr" ]

WORKDIR /workspaces/CrossMgr

RUN git config --global --add safe.directory /workspaces/CrossMgr